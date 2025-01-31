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
    with picamera2.Picamera2() as camera:
        camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
        encoder = JpegEncoder()
        output1 = FfmpegOutput("temp.mp4", audio=False)
        output3 = StreamingOutput()
        output2 = FileOutput(output3)
        encoder.output = [output1, output2]

        camera.start_encoder(encoder)
        camera.start()
        output1.start()
        time.sleep(20)
        output1.stop()
        print("done")
        while True:
            with output3.condition:
                output3.condition.wait()
            frame = output3.frame
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


# defines the route that will access the video feed and call the feed function
class video_feed(Resource):
    def get(self):
        return Response(
            genFrames(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


api.add_resource(video_feed, "/cam")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
