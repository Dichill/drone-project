from flask import Flask, Response
import cv2
import time
import os

app = Flask(__name__)


def list_video_devices():
    """List all available video devices using v4l2-ctl"""
    print("Checking video devices with v4l2-ctl...")
    os.system("v4l2-ctl --list-devices")


def init_camera():
    """Initialize camera using libcamera's V4L2 compatibility layer"""
    # Try different device indices for libcamera-v4l2
    for index in [0, 2, 4]:  # Common libcamera device indices
        try:
            camera = cv2.VideoCapture(index)
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            if camera.isOpened() and camera.read()[0]:
                print(f"Found camera at index {index}")
                return camera
        except:
            continue

    raise RuntimeError(
        """
    No camera found. Required setup:
    1. Enable camera in raspi-config (Interface Options > Camera)
    2. Install libcamera-v4l2: sudo apt install libcamera-v4l2
    3. Load driver: sudo modprobe bcm2835-v4l2
    4. Reboot and verify with: v4l2-ctl --list-devices
    """
    )


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
    print("Available video devices:")
    os.system("ls -l /dev/video*")
    app.run(host="0.0.0.0", port=5000, debug=False)
