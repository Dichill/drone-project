import picamera2  # camera module for RPi camera
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput
import io

from flask import Flask, Response
from flask_restful import Resource, Api
from threading import Condition
import cv2
import numpy as np
from cv2 import aruco

# Flask setup
app = Flask(__name__)
api = Api(app)


# Class responsible for handling streamed frames
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


# Initialize the ArUco marker detection
ARUCO_DICT = aruco.Dictionary_get(aruco.DICT_6X6_250)  # Choose ArUco dictionary
ARUCO_PARAMS = aruco.DetectorParameters_create()


# Function to generate video frames with ArUco marker detection
def genFrames():
    with Picamera2() as camera:
        camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
        encoder = JpegEncoder()
        output1 = FfmpegOutput("temp.mp4", audio=False)  # Optional file recording
        output3 = StreamingOutput()
        output2 = FileOutput(output3)
        encoder.output = [output1, output2]

        # Start the camera and encoder
        camera.start_encoder(encoder)
        camera.start()
        output1.start()
        time.sleep(20)  # Optional waiting period for recording
        output1.stop()
        print("Recording stopped. Streaming started.")

        while True:
            with output3.condition:
                output3.condition.wait()
                frame = output3.frame

            if frame:
                # Convert JPEG bytes to numpy array for OpenCV
                img_array = np.frombuffer(frame, dtype=np.uint8)

                # Decode image using OpenCV
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                # --- ArUco Marker Detection ---
                # Convert image to grayscale for detection
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # Detect ArUco markers
                corners, ids, rejected = aruco.detectMarkers(
                    gray, ARUCO_DICT, parameters=ARUCO_PARAMS
                )

                # If markers are detected, draw them on the image
                if ids is not None:
                    # Draw detected markers (bounding polygons and IDs)
                    aruco.drawDetectedMarkers(img, corners, ids)

                    # Optional: Print detected marker IDs to the console
                    print(f"Detected marker IDs: {ids.flatten()}")

                # Convert processed image back to JPEG bytes
                ret, jpeg = cv2.imencode(".jpg", img)
                if ret:
                    frame = jpeg.tobytes()

            # Stream the processed frame
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


# Flask RESTful route for accessing the video feed
class video_feed(Resource):
    def get(self):
        return Response(
            genFrames(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


# Add the API resource
api.add_resource(video_feed, "/cam")

# Main entry point
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
