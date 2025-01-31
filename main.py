from flask import Flask, Response
import cv2
import time

app = Flask(__name__)

def initialize_camera():
    """
    Initialize camera with specific settings for ArduCam IMX708
    Returns configured camera object or None on failure
    """
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        return None
    
    # Configure camera settings for ArduCam IMX708
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    camera.set(cv2.CAP_PROP_FPS, 30)
    
    # Add a small delay to allow camera to initialize
    time.sleep(2)
    return camera

# Initialize the camera with proper settings
camera = initialize_camera()

@app.route("/")
def index():
    return "Camera Streaming: Visit /video_feed to view the live stream"

@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            # Add delay to prevent timeout
            time.sleep(0.033)  # ~30 FPS
            
            if not camera.isOpened():
                print("Camera disconnected. Attempting to reinitialize...")
                global camera
                camera = initialize_camera()
                if camera is None:
                    break
                
            # Read a single frame from the camera with timeout handling
            retry_count = 0
            while retry_count < 3:
                success, frame = camera.read()
                if success:
                    break
                print(f"Frame capture failed, attempt {retry_count + 1}/3")
                time.sleep(0.1)
                retry_count += 1
            
            if not success:
                print("Failed to capture frame after retries")
                continue
                
            try:
                # Encode the frame as JPEG
                _, buffer = cv2.imencode(".jpg", frame)
                frame_data = buffer.tobytes()
                # Yield the frame in a multipart response format
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n"
                )
            except Exception as e:
                print(f"Error encoding frame: {str(e)}")
                continue

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    try:
        if camera is None:
            print("Failed to initialize camera")
            exit(1)
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        if camera is not None:
            camera.release()
