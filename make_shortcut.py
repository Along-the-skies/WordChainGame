import os
import sys
import time
import shutil
import traceback
from pathlib import Path

try:
    import pythoncom
    from win32com.client import Dispatch
except Exception as e:
    print("Failed to import pywin32.")
    print(e)
    input("Press Enter to exit...")
    sys.exit(1)


def create_shortcut(shortcut_path: Path, target: Path, icon: Path):
    print("\n" + "=" * 60)
    print("Creating Shortcut")
    print("=" * 60)
    print(f"Shortcut : {shortcut_path}")
    print(f"Target   : {target}")
    print(f"Icon     : {icon}")

    pythoncom.CoInitialize()

    try:
        shell = Dispatch("WScript.Shell")

        if shortcut_path.exists():
            print("Existing shortcut found. Removing...")
            shortcut_path.unlink()

        shortcut = shell.CreateShortcut(str(shortcut_path))

        # Launch batch directly
        shortcut.TargetPath = str(target)
        shortcut.WorkingDirectory = str(target.parent)
        shortcut.Description = "Launch Word Chain Game - Multiplayer"

        if icon.exists():
            shortcut.IconLocation = str(icon)

        print("Saving shortcut...")
        shortcut.Save()

        # Give Windows a moment
        time.sleep(2)

        print("\nVerification")
        print("-" * 30)
        print("Path:", shortcut_path)
        print("Exists:", shortcut_path.exists())

        if shortcut_path.exists():
            print("Size:", shortcut_path.stat().st_size, "bytes")
            print("SUCCESS!")
            return True
        else:
            print("FAILED! Shortcut does not exist after Save().")
            return False

    except Exception:
        traceback.print_exc()
        return False

    finally:
        pythoncom.CoUninitialize()


def main():
    base = Path(__file__).resolve().parent
    # Determine repository root: either current dir or its parent
    if (base / 'Launcher').exists():
        repo_root = base
    elif (base.parent / 'Launcher').exists():
        repo_root = base.parent
    else:
        repo_root = base

    # Launcher exe in Launcher folder (single-file publish expected)
    launcher = repo_root / "Launcher" / "WordChainGameLauncher.exe"
    icon = repo_root / "icon.ico"

    print("=" * 70)
    print("Word Chain Game Shortcut Creator")
    print("=" * 70)

    print("Base Folder :", repo_root)
    print("Launcher    :", launcher)
    print("Icon        :", icon)
    print()

    if not launcher.exists():
        print("ERROR: Launcher not found!")
        input("Press Enter...")
        return

    desktop = Path(os.environ["USERPROFILE"]) / "Desktop"

    start_menu = (
        Path(os.environ["APPDATA"])
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
    )

    desktop.mkdir(parents=True, exist_ok=True)
    start_menu.mkdir(parents=True, exist_ok=True)

    desktop_shortcut = desktop / "Word Chain Game - Multiplayer.lnk"
    start_shortcut = start_menu / "Word Chain Game - Multiplayer.lnk"

    print("\nCreating Desktop Shortcut...")
    desktop_ok = create_shortcut(desktop_shortcut, launcher, icon)

    print("\nCreating Start Menu Shortcut...")
    start_ok = create_shortcut(start_shortcut, launcher, icon)

    # If COM failed for Start Menu but Desktop exists, try copying
    if not start_ok and desktop_shortcut.exists():
        print("\nAttempting fallback copy from Desktop...")
        try:
            shutil.copy2(desktop_shortcut, start_shortcut)
            time.sleep(1)

            if start_shortcut.exists():
                print("Fallback copy SUCCESS!")
                start_ok = True
            else:
                print("Fallback copy FAILED!")
        except Exception:
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Desktop Shortcut : {'SUCCESS' if desktop_ok else 'FAILED'}")
    print(f"Start Shortcut   : {'SUCCESS' if start_ok else 'FAILED'}")

    print("\nDesktop Exists :", desktop_shortcut.exists())
    print("Start Exists   :", start_shortcut.exists())

    if desktop_shortcut.exists():
        print("Desktop Size  :", desktop_shortcut.stat().st_size)

    if start_shortcut.exists():
        print("Start Size    :", start_shortcut.stat().st_size)

    print("\nDesktop Path:")
    print(desktop_shortcut)

    print("\nStart Menu Path:")
    print(start_shortcut)

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("\nPress Enter to exit...")