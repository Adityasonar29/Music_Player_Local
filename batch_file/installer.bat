@echo off
REM ==========================================
REM Modular Music Player Installer
REM ==========================================


REM Directory where this BAT lives
set SCRIPT_DIR=%~dp0

REM Project root (one level up from batch_file)
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Main CLI script
set CLI_SCRIPT=%PROJECT_ROOT%\setup_files\installer.py

REM Virtual environment location
set VENV_DIR=%PROJECT_ROOT%\.venv



REM ------------------------------------------
REM Activate venv
REM ------------------------------------------
call "%VENV_DIR%\Scripts\activate.bat"
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to activate virtual environment
    exit /b 1
)


REM ------------------------------------------
REM Run installer and pass arguments
REM ------------------------------------------
python "%CLI_SCRIPT%" %*