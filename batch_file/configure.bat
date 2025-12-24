@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ===============================
echo Music Player Setup & Launcher
echo ===============================

:: -------------------------------------------------
:: 1. Check if Python exists
:: -------------------------------------------------
where python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ ERROR: Python is not installed or not added to PATH.
    echo 👉 Install Python from: https://www.python.org/downloads/
    echo 👉 During installation, CHECK "Add Python to PATH"
    pause
    exit /b 1
)

echo ✅ Python detected

:: -------------------------------------------------
:: 3. Create virtual environment
:: -------------------------------------------------
IF NOT EXIST .venv (
    echo 🔧 Creating virtual environment...
    python -m venv .venv
)

:: -------------------------------------------------
:: 4. Activate venv
:: -------------------------------------------------
call .venv\Scripts\activate
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment activated

:: -------------------------------------------------
:: 5. Install requirements
:: -------------------------------------------------
IF NOT EXIST requirements.txt (
    echo ❌ requirements.txt not found
    pause
    exit /b 1
)

echo 📦 Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Dependency installation failed
    pause
    exit /b 1
)

echo ✅ Dependencies installed

:: -------------------------------------------------
:: 6. Install the package in development mode
:: -------------------------------------------------
IF NOT EXIST setup.py (
    echo ❌ setup.py not found
    pause
    exit /b 1
)

echo ⚙ Installing package in development mode...
pip install -e .

IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Package installation failed
    pause
    exit /b 1
)

echo ✅ Package installed

:: -------------------------------------------------
:: 7. Check CLI command availability
:: -------------------------------------------------
where musicplayer >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ CLI command "musicplayer" not found in PATH
    echo 👉 Environment variable not updated or CLI not installed correctly
    pause
    exit /b 1
)

echo ✅ CLI command available


:: -------------------------------------------------
:: 8. Open browser via Python
:: -------------------------------------------------
echo ⤵️ Starting the launcher
python setup_files\launcher.py

:: Wait a bit for server to start
timeout /t 5 /nobreak >nul
echo ✅ launcher started

:: -------------------------------------------------
:: 9. Start server
:: -------------------------------------------------
echo 🚀 Starting music server...
musicplayer server start
echo ✅ Music server started

pause
endlocal