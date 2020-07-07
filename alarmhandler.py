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

    def __init__(self, bufSize=10, timeout=5.0):
        self.timeout = timeout
        self.Q = Queue(maxsize=bufSize)
        self.thread = None
        self.started = False

    def sendEvent(self, event):
        logging.info("Event received " + event)
        self.Q.put(event)

    def start(self, username, password, emailToSend):
        self.thread = Thread(target=self.eventListener, args=())
        self.thread.daemon = True
        self.thread.start()
        self.username = username
        self.password = password
        self.emailToSend = emailToSend
        self.started = True

    def eventListener(self):
        logging.info("AlarmHandler started")

        while True:
            logging.info("Mail server waiting....")
            if not self.started:
                return

            if not self.Q.empty():
                event = self.Q.get()
                logging.info("Started sending email to " +
                             self.emailToSend + " with event " + event)
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
        with yagmail.SMTP(self.username, self.password) as yag:
            timestamp = datetime.datetime.now()
            yag.send(to=self.emailToSend, subject='Motion detected!', contents='Motion detected at {}'.format(
                timestamp.strftime("%A %d %B %Y %I:%M:%S%p")), attachments=[videofile])
            logging.info('Email sent.')
