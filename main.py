from flask import Flask, Response
import cv2
import time

app = Flask(__name__)


# Camera initialization with Arducam IMX708 specific settings
def init_camera():
    # Libcamera-specific GStreamer pipeline for IMX708
    pipeline = (
        "libcamerasrc ! "
        "video/x-raw,width=1920,height=1080,framerate=30/1 ! "
        "videoconvert ! "
        "video/x-raw,format=BGR ! "
        "appsink drop=1"
    )

    camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

    if not camera.isOpened():
        raise RuntimeError(
            """
        Failed to open camera. Ensure:
        1. Camera is enabled in raspi-config
        2. libcamera-dev is installed: sudo apt install libcamera-dev
        3. GStreamer plugins are installed: sudo apt install gstreamer1.0-plugins-bad
        """
        )

    print(f"Camera initialized via {camera.getBackendName()} with libcamera pipeline")
    return camera


camera = init_camera()


@app.route("/")
def index():
    return "Camera Streaming: Visit /video_feed to view the live stream"


@app.route("/video_feed")
def video_feed():
    def generate():
        global camera
        while True:
            try:
                success, frame = camera.read()
                if not success:
                    print("Frame read failed, reinitializing camera...")
                    camera.release()
                    time.sleep(1)
                    camera = init_camera()
                    continue

                # Resize frame for better performance
                frame = cv2.resize(frame, (640, 480))
                _, buffer = cv2.imencode(
                    ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                )
                frame_data = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n"
                )

            except Exception as e:
                print(f"Camera error: {str(e)}")
                break

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
