import subprocess
import shutil
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, ".venv")
PID_FILE = os.path.join(ROOT, "music_server.pid")

def run(cmd):
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("Stopping server if running...")
run(["musicplayer", "server", "stop"])

print("Removing CLI...")
run([sys.executable, "-m", "pip", "uninstall", "-y", "moduler-musicplayer"])

if os.path.exists(VENV):
    print("Removing virtual environment...")
    shutil.rmtree(VENV)

if os.path.exists(PID_FILE):
    os.remove(PID_FILE)

print("System restored successfully.")
