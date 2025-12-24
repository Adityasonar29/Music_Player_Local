import os
import time
import logging
import sys

from music_server_files.music_cli import start_server_in_background, stop_server_in_background, server_check
from util.open_web import open

from dotenv import dotenv_values
env_vars = dotenv_values(".env")

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "launcher.log")

PID_FILE = os.path.join(ROOT, "music_server.pid")
APP_URL = env_vars.get("MUSIC_SERVER_URL", "http://localhost:5555")  # Get URL from .env

FRONT_END = "./spotify_music_player.html"
APP_NAME = "Music Player"

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def start_server():
    logging.info("Starting server")
    stop_server_in_background()
    time.sleep(2)
    start_server_in_background()  # Make sure to actually start the server

def stop_server():
    logging.info("Stopping server")
    stop_server_in_background()

def wait_for_server(timeout=30):
    """Wait for server to be ready"""
    import requests
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{APP_URL}/status", timeout=1)
            if response.status_code == 200:
                logging.info("Server is ready")
                return True
        except:
            time.sleep(1)
    logging.error("Server did not start in time")
    return False

def open_browser():
    open()
    # Fallback to default browser
    logging.info("Opening in default browser")
    return None

# MAIN
logging.info("Launcher started")

# Start server if not running
if not server_check():
    start_server()
    if not wait_for_server():
        logging.error("Server failed to start")
        sys.exit(1)
else:
    logging.info("Server is already running")

# Open browser
open_browser()
