import os
import sys
import webbrowser
import shutil

def open():
    HTML_FILE = "spotify_music_player.html"  # change if needed

    def fail(msg):
        print(f"❌ {msg}")
        sys.exit(1)

    # Check HTML file
    if not os.path.exists(HTML_FILE):
        fail(f"HTML file not found: {HTML_FILE}")

    # Try Chrome first
    chrome_path = shutil.which("chrome") or shutil.which("chrome.exe")
    if chrome_path:
        webbrowser.register(
            "chrome",
            None,
            webbrowser.BackgroundBrowser(chrome_path),
        )
        webbrowser.get("chrome").open_new_tab(os.path.abspath(HTML_FILE))
        print("✅ Opened HTML in Google Chrome")
    else:
        print("⚠ Chrome not found. Opening with default browser.")
        webbrowser.open_new_tab(os.path.abspath(HTML_FILE))
