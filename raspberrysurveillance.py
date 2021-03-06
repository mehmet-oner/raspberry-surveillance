from pyimagesearch.keyclipwriter import KeyClipWriter
from pyimagesearch.singlemotiondetector import SingleMotionDetector
from imutils.video import VideoStream
from flask import Response
from flask import Flask
from flask import render_template
from flask_cors import CORS
import threading
import argparse
import datetime
import imutils
import time
import cv2
import logging
from alarmhandler import AlarmHandler

# Configure logger
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

fps = 15
outputFrame = None
# 5 seconds recording before and after the motion
beforeAndAfterFrames = fps * 5

lock = threading.Lock()

app = Flask(__name__)
CORS(app)

vs = VideoStream(src=0, framerate=fps).start()
time.sleep(3.0)
logging.info("Application started")


@app.route("/")
def index():
    return render_template("index.html")


def detect_motion(outputDirectory):
    global vs, outputFrame, lock

    frameCount = 32
    md = SingleMotionDetector(accumWeight=0.1)
    total = 0

    recordedFrameCount = 0
    kcw = KeyClipWriter(bufSize=beforeAndAfterFrames)
    lastFileName = None

    while True:
        # read the next frame from the video stream, resize it,
        # convert the frame to grayscale, and blur it
        frame = vs.read()
        frame = imutils.resize(frame, width=600)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)

        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime(
            "%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        if total > frameCount:

            kcw.update(frame)

            motion = md.detect(gray)

            # check to see if motion was found in the frame
            if motion is not None:
                # unpack the tuple and draw the box surrounding the
                # "motion area" on the output frame
                (thresh, (minX, minY, maxX, maxY)) = motion
                cv2.rectangle(frame, (minX, minY),
                              (maxX, maxY), (0, 0, 255), 2)
                if kcw.recording is False:
                    recordedFrameCount = 0
                    timestamp = datetime.datetime.now()
                    lastFileName = "{}/{}.mp4".format(outputDirectory,
                                                      timestamp.strftime("%Y%m%d-%H%M%S"))
                    kcw.start(lastFileName,
                              cv2.VideoWriter_fourcc(*"MP4V"), fps)
                    logging.info("Started recording")

            if kcw.recording is True:
                recordedFrameCount += 1

                if recordedFrameCount > beforeAndAfterFrames:
                    logging.info("Stopped recording")
                    kcw.finish()
                    if lastFileName is not None:
                        ah.sendEvent(lastFileName)

        # update the background model and increment the total number
        # of frames read thus far
        md.update(gray)
        total += 1

        # acquire the lock, set the output frame, and release the
        # lock
        with lock:
            outputFrame = frame.copy()


def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock

    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
              bytearray(encodedImage) + b'\r\n')


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/start")
def startRecording():
    logging.debug("TODO: Start recording")
    return Response("Started")


@app.route("/stop")
def stopRecording():
    logging.debug("TODO: Stopped recording")
    return Response("Stopped")

# check to see if this is the main thread of execution
if __name__ == '__main__':
    # construct the argument parser and parse command line arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--ip", type=str, required=True,
                    help="ip address of the device")
    ap.add_argument("-o", "--port", type=int, required=True,
                    help="ephemeral port number of the server (1024 to 65535)")
    ap.add_argument("-dir", "--dir", type=str, required=True,
                    help="directory to store the clips")
    ap.add_argument("-username", "--username", type=str, required=True,
                    help="Smtp username")
    ap.add_argument("-password", "--password", type=str, required=True,
                    help="Smtp password")
    ap.add_argument("-email", "--email", type=str, required=True,
                    help="Email to send")

    args = vars(ap.parse_args())

    ah = AlarmHandler(bufSize=10, timeout=5.0)
    ah.start(args["username"], args["password"], args["email"])

    # start a thread that will perform motion detection
    t = threading.Thread(target=detect_motion, args=(
        args["dir"],))
    t.daemon = True
    t.start()

    # start the flask app
    app.run(host=args["ip"], port=args["port"], debug=True,
            threaded=True, use_reloader=False)

# release the video stream pointer
vs.stop()
ah.finish()
