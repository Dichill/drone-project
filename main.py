import picamera2  # camera module for RPi camera
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput
import io

import subprocess
from flask import Flask, Response
from flask_restful import Resource, Api, reqparse, abort
import atexit
from datetime import datetime
from threading import Condition
import time

import cv2
import numpy as np

app = Flask(__name__)
api = Api(app)


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


# defines the function that generates our frames
def genFrames():
    with Picamera2() as camera:
        # Configure for raw sensor output instead of JPEG
        config = camera.create_video_configuration(
            main={"size": (640, 480)}, encode="raw"
        )
        camera.configure(config)

        # Create separate output for streaming
        output3 = StreamingOutput()
        encoder = JpegEncoder()
        output2 = FileOutput(output3)
        encoder.output = [output2]

        camera.start_encoder(encoder)
        camera.start()

        # Initialize ArUco detector once
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()

        try:
            while True:
                with output3.condition:
                    output3.condition.wait()
                    frame = output3.frame

                if frame is None:
                    continue  # Skip empty frames

                # Convert to numpy array with bounds checking
                img_array = np.frombuffer(frame, dtype=np.uint8)
                if img_array.size == 0:
                    continue

                # Decode with error checking
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is None:
                    continue

                try:
                    # Detect markers with safety checks
                    corners, ids, rejected = cv2.aruco.detectMarkers(
                        img, aruco_dict, parameters=parameters
                    )

                    if ids is not None:
                        cv2.aruco.drawDetectedMarkers(img, corners, ids)
                except cv2.error as e:
                    print(f"OpenCV error: {e}")
                    continue

                # Encode with quality check
                ret, jpeg = cv2.imencode(
                    ".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                )
                if ret and jpeg is not None:
                    frame = jpeg.tobytes()
                else:
                    frame = b""  # Fallback empty frame

                yield (
                    b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )

        finally:
            camera.stop_encoder()
            camera.stop()


# defines the route that will access the video feed and call the feed function
class video_feed(Resource):
    def get(self):
        return Response(
            genFrames(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


api.add_resource(video_feed, "/cam")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
