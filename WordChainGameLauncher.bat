@echo off
title WordChain Installer / Updater
setlocal EnableDelayedExpansion

REM ===============================
REM Configuration
REM ===============================

set "GAME_DIR=%~dp0WordChainGame"

if not exist "%GAME_DIR%" mkdir "%GAME_DIR%"
cd /d "%GAME_DIR%"

echo.
echo Checking Python installation...
echo.

:CheckPython
python --version >nul 2>&1
if !errorlevel! neq 0 (
    for /f "tokens=2*" %%A in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "SYS_PATH=%%B"
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path') do set "USER_PATH=%%B"
    set "PATH=!SYS_PATH!;!USER_PATH!"
    
    python --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo Python not found.
        echo Installing Python using winget...
        winget install Python.Python.3.12 --silent
        
        echo Waiting for installation to complete and refreshing path...
        timeout /t 15 >nul
        goto CheckPython
    )
)

echo.
echo Checking pip...
echo.

python -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    python -m ensurepip --upgrade
)

echo.
echo Checking for updates natively via Python...
echo.

REM --- Create a clean inline Python helper script to handle networking/unzipping safely ---
(
echo import urllib.request, zipfile, os, shutil
echo VERSION_URL = "https://raw.githubusercontent.com/Along-the-skies/WordChainGame/refs/heads/main/version.txt"
echo REPO_ZIP = "https://github.com/Along-the-skies/WordChainGame/archive/refs/heads/main.zip"
echo def check_and_update^(^):
echo     try:
echo         req = urllib.request.Request^(VERSION_URL, headers={'User-Agent': 'Mozilla/5.0'}^)
echo         with urllib.request.urlopen^(req^) as r: remote_v = r.read^(^).decode^(^'utf-8^'^).strip^(^)
echo     except Exception as e:
echo         print^(f"[Error] Network check failed: {e}"^); return False
echo     local_v = ""
echo     if os.path.exists^("version.txt"^):
echo         with open^("version.txt", "r"^) as f: local_v = f.read^(^).strip^(^)
echo     if local_v == remote_v:
echo         print^("Game is up to date."^); return True
echo     print^("New version found. Downloading update..."^)
echo     try:
echo         req_zip = urllib.request.Request^(REPO_ZIP, headers={'User-Agent': 'Mozilla/5.0'}^)
echo         with urllib.request.urlopen^(req_zip^) as r, open^("update.zip", "wb"^) as out: out.write^(r.read^(^)^)
echo         with zipfile.ZipFile^("update.zip", "r"^) as zip_ref: zip_ref.extractall^("temp_extract"^)
echo         src_dir = os.path.join^("temp_extract", "WordChainGame-main"^)
echo         if os.path.exists^(src_dir^):
echo             for item in os.listdir^(src_dir^):
echo                 s = os.path.join^(src_dir, item^); d = os.path.join^(".", item^)
echo                 if os.path.isdir^(s^):
echo                     if os.path.exists^(d^): shutil.rmtree^(d^)
echo                     shutil.copytree^(s, d^)
echo                 else: shutil.copy2^(s, d^)
echo         with open^("version.txt", "w"^) as f: f.write^(remote_v^)
echo         if os.path.exists^("update.zip"^): os.remove^("update.zip"^)
echo         if os.path.exists^("temp_extract"^): shutil.rmtree^("temp_extract"^)
echo         print^("Update applied successfully."^); return True
echo     except Exception as e:
echo         print^(f"[Error] Update failed: {e}"^); return False
echo check_and_update^(^)
) > updater.py

REM Run the updater script cleanly via Python
python updater.py
del updater.py >nul 2>&1

REM Upgrade pip and sync dependencies safely
python -m pip install --upgrade pip >nul 2>&1
if exist requirements.txt (
    echo Syncing dependencies...
    python -m pip install -r requirements.txt --quiet
)

echo Launching game...
if exist game.py (
    start "" python game.py
    exit
) else (
    echo [ERROR] Game file (game.py) was not found in the directory.
    pause
)