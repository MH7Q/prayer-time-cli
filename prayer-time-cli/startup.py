import sys
import os
import platform

APP_NAME = "PrayerStation"

def set_startup(enable: bool):
    """
    Enables or Disables the app running on system startup.
    Supports Windows and Linux.
    """
    system = platform.system()
    
    # Get the command to run this script
    # We use sys.executable to get 'python.exe' and sys.argv[0] for 'main.py'
    python_exe = sys.executable
    script_path = os.path.abspath(sys.argv[0])
    # Wrap in quotes to handle spaces in paths
    cmd = f'"{python_exe}" "{script_path}"'

    if system == "Windows":
        _windows_startup(enable, cmd)
    elif system == "Linux":
        _linux_startup(enable, cmd)

def _windows_startup(enable, cmd):
    # Path to the User Startup folder
    startup_folder = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    bat_path = os.path.join(startup_folder, f"{APP_NAME}.bat")

    if enable:
        # Create a .bat file that launches the python script
        # "pythonw" is better for background (no terminal), but "python" is safer for testing.
        # We use pythonw.exe if available to hide the console on startup
        cmd = cmd.replace("python.exe", "pythonw.exe")
        with open(bat_path, "w") as f:
            f.write(f'@echo off\n{cmd}\nexit')
    else:
        if os.path.exists(bat_path):
            os.remove(bat_path)

def _linux_startup(enable, cmd):
    # Path to autostart folder
    autostart_folder = os.path.expanduser("~/.config/autostart")
    desktop_file = os.path.join(autostart_folder, f"{APP_NAME}.desktop")

    if enable:
        if not os.path.exists(autostart_folder):
            os.makedirs(autostart_folder)
        
        content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec={cmd}
X-GNOME-Autostart-enabled=true
"""
        with open(desktop_file, "w") as f:
            f.write(content)
    else:
        if os.path.exists(desktop_file):
            os.remove(desktop_file)