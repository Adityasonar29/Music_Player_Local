import subprocess
import sys
import os
import shutil
import logging

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "installer.log")

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def fail(msg):
    logging.error(msg)
    print(f"❌ {msg}")
    sys.exit(1)

def run(cmd, shell=False):
    logging.info(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=shell)
    if result.returncode != 0:
        fail(f"Command failed: {cmd}")

# 2. Run configure.bat ONCE
print("🔧 Configuring environment...")
run(["cmd", "/c", "batch_file\\configure.bat"])


print("✅ Installation completed successfully.")
logging.info("Installer finished successfully.")
