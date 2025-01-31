from flask import Flask, Response
import cv2

app = Flask(__name__)

# Initialize the camera (0 for the default camera, increase if you have multiple cameras)
camera = cv2.VideoCapture(0)


@app.route("/")
def index():
    return "Camera Streaming: Visit /video_feed to view the live stream"


@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            # Read a single frame from the camera
            success, frame = camera.read()
            if not success:
                break
            else:
                # Encode the frame as JPEG
                _, buffer = cv2.imencode(".jpg", frame)
                frame_data = buffer.tobytes()
                # Yield the frame in a multipart response format
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n"
                )

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
