from flask import Flask, Response
import cv2
import time

app = Flask(__name__)


# Camera initialization with Arducam IMX708 specific settings
def init_camera():
    # Use libcamera's V4L2 compatibility layer
    camera = cv2.VideoCapture(
        "libcamerasrc ! video/x-raw,width=1920,height=1080 ! videoconvert ! appsink",
        cv2.CAP_GSTREAMER,
    )

    if not camera.isOpened():
        # Fallback to traditional V4L2 with buffer size adjustment
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize latency
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        camera.set(cv2.CAP_PROP_FPS, 15)  # Start with lower FPS

    # Additional diagnostic checks
    if not camera.isOpened():
        raise RuntimeError("Cannot open camera - check libcamera setup")

    print(f"Camera initialized: {camera.getBackendName()}")
    time.sleep(2)  # Warm-up time
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
