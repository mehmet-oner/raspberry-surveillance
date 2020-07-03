from collections import deque
from threading import Thread
from queue import Queue
import time
import yagmail
import datetime
import logging

# Configure logger
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


class AlarmHandler:

    def __init__(self, bufSize=10, timeout=1.0, username, password, emailToSend):
        self.timeout = timeout
        self.Q = Queue(maxsize=bufSize)
        self.thread = None
        self.started = False

    def sendEvent(self, event):
        self.Q.put(event)

    def start(self):
        self.thread = Thread(target=self.eventListener, args=())
        self.thread.daemon = True
        self.thread.start()
        self.started = True
        logging.info("AlarmHandler started")

    def eventListener(self):
        while True:
            if not self.started:
                return

            if not self.Q.empty():
                event = self.Q.get()
                self.sendMail(event)
            else:
                time.sleep(self.timeout)

    def flush(self):
        while not self.Q.empty():
            event = self.Q.get()
            self.sendMail(event)

    def finish(self):
        self.started = False
        self.thread.join()
        self.flush()
        logging.info("AlarmHandler ended")

    def sendMail(self, videofile=""):
        with yagmail.SMTP(username, password) as yag:
            timestamp = datetime.datetime.now()
            yag.send(to=emailToSend, subject='Motion detected!', contents='Motion detected at {}'.format(
                timestamp.strftime("%A %d %B %Y %I:%M:%S%p")), attachments=[videofile])
            logging.info('Email sent.')
