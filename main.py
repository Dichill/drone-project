from flask import Flask, Response
from picamera2 import Picamera2
import io
from PIL import Image

app = Flask(__name__)

# Create a Picamera2 instance
picam2 = Picamera2()

# Configure the camera for preview
camera_config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(camera_config)
picam2.start()


@app.route("/")
def index():
    """Root URL: brief instructions"""
    return "Go to /video_feed to view the camera stream."


@app.route("/video_feed")
def video_feed():
    """Stream the camera video feed."""

    def generate():
        while True:
            # Capture a frame from the camera
            frame = picam2.capture_array()

            # Convert the frame to a JPEG image
            image = Image.fromarray(frame)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            frame_data = buffer.getvalue()

            # Yield the frame in multipart format for MJPEG streaming
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n"
            )

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
