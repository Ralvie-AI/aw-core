import sys 
import platform

import win32file
import pywintypes

PIPE_NAME = r'\\.\pipe\AppSocket'

def is_macos():
    """Check if the current OS is macOS."""
    # logger.info("Checking the operating system.")
    return platform.system() == 'Darwin'

def is_windows():
  return platform.system() == "Windows"

def get_window_version():
    version = sys.getwindowsversion()
    if version.major == 10 and version.build >= 22000:
        return 11
    else:
        return 10
 
def send_to_gui(msg: str):
    try:
        handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_WRITE,
            0,  # No sharing
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        win32file.WriteFile(handle, msg.encode())
        win32file.CloseHandle(handle)
        return True
    except pywintypes.error as e:
        print(f"[ERROR] Could not send: {e}")
        return False
    