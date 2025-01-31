from flask import Flask, Response
import cv2
import time

app = Flask(__name__)


# Camera initialization with Arducam IMX708 specific settings
def init_camera():
    camera = cv2.VideoCapture(0)

    # Set camera parameters for Arducam IMX708
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)  # Max width for IMX708
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)  # Max height for IMX708
    camera.set(cv2.CAP_PROP_FPS, 30)  # Set frame rate
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    # Allow extra time for camera initialization
    time.sleep(2)  # Important for Arducam initialization

    if not camera.isOpened():
        raise RuntimeError("Could not open camera")
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
