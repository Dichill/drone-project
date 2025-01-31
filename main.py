import signal
import sys
import picamera2
from picamera2.encoders import H264Encoder  # More efficient than JPEG
from picamera2.outputs import FileOutput
from flask import Flask, Response
from threading import Condition, Event
import time

# Use production WSGI server instead of Flask dev server
from waitress import serve

app = Flask(__name__)
exit_event = Event()


class OptimizedStreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()
        self.last_active = time.time()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.last_active = time.time()
            self.condition.notify_all()


def optimized_frame_generator(output):
    """Yield frames with activity-based timeout and resource cleanup"""
    try:
        timeout = 30  # Seconds of inactivity before shutdown
        while not exit_event.is_set():
            with output.condition:
                output.condition.wait(timeout=1)
                if time.time() - output.last_active > timeout:
                    print("No clients connected - suspending stream")
                    break
                frame = output.frame
            yield (b"--frame\r\nContent-Type: video/h264\r\n\r\n" + frame + b"\r\n")
    finally:
        print("Closing generator resources")


def configure_low_power_camera():
    """Configure camera for minimal power consumption"""
    config = picamera2.Picamera2().create_video_configuration(
        main={
            "size": (320, 240),  # Reduced resolution
            "format": "YUV420",  # Native sensor format
        },
        controls={
            "FrameRate": 15,  # Reduced frame rate
            "AnalogueGain": 1.0,  # Minimize analog gain
            "AwbMode": "Greyworld",  # Simpler white balance
            "ExposureTime": 10000,  # Fixed exposure
        },
        buffer_count=2,  # Minimal buffers
    )
    return config


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    print("\nShutting down gracefully...")
    exit_event.set()
    sys.exit(0)


@app.route("/cam")
def video_feed():
    """Streaming endpoint with activity monitoring"""
    try:
        return Response(
            optimized_frame_generator(output),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
    except Exception as e:
        print(f"Streaming error: {e}")
        raise


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    with picamera2.Picamera2() as camera:
        config = configure_low_power_camera()
        camera.configure(config)

        output = OptimizedStreamingOutput()
        encoder = H264Encoder(
            bitrate=500000,  # Lower bitrate
            repeat=True,  # Repeat headers for streaming
            profile="Main",  # Better compression
        )
        encoder.output = FileOutput(output)

        camera.start_encoder(encoder)
        camera.start()

        try:
            serve(app, host="0.0.0.0", port=5000, threads=2)  # Production server
        finally:
            camera.stop_encoder()
            camera.stop()
