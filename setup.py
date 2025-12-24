from setuptools import setup

setup(
    name="moduler-musicplayer",
    version="1.0.0",
    py_modules=["music_cli"],  # Keep original module
    entry_points={
        "console_scripts": [
            "musicplayer=music_cli:app"  # Changed to cli.py
        ]
    },
)