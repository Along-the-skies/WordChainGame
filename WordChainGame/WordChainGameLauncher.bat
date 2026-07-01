@echo off
title Word Chain Installer / Updater
setlocal EnableDelayedExpansion

REM ===============================
REM Configuration
REM ===============================

set GAME_DIR=%~dp0WordChainGame
set REPO_RAW=https://github.com/Along-the-skies/WordChainGame.git


if not exist "%GAME_DIR%" mkdir "%GAME_DIR%"

cd /d "%GAME_DIR%"

echo.
echo Checking Python installation...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found.
    echo Installing Python using winget...

    winget install Python.Python.3.12 --silent

    echo Waiting for installation...
    timeout /t 10 >nul
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Failed to install Python.
    pause
    exit
)

echo.
echo Checking pip...
echo.

python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    python -m ensurepip --upgrade
)

echo Downloading latest files...

powershell -Command ^
"Invoke-WebRequest '%REPO_RAW%/version.txt' -OutFile 'remote_version.txt'"

if not exist version.txt (
    set UPDATE=1
) else (
    set /p LOCAL=<version.txt
    set /p REMOTE=<remote_version.txt

    if "!LOCAL!"=="!REMOTE!" (
        set UPDATE=0
    ) else (
        set UPDATE=1
    )
)

if "!UPDATE!"=="1" (
    echo Updating game...

    powershell -Command ^
    "Invoke-WebRequest '%REPO_RAW%/game.py' -OutFile 'game.py'"

    powershell -Command ^
    "Invoke-WebRequest '%REPO_RAW%/launcher.py' -OutFile 'launcher.py'"

    powershell -Command ^
    "Invoke-WebRequest '%REPO_RAW%/requirements.txt' -OutFile 'requirements.txt'"

    copy /Y remote_version.txt version.txt >nul

    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
)

del remote_version.txt >nul 2>&1

echo Launching game...
python game.py

pause