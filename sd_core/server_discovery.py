import json
import os
import sys
import ctypes
from pathlib import Path
from typing import Optional
from sd_core.dirs import get_data_dir  # Replace with your actual sd_core data dir helper

def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        # WaitForSingleObject with 0ms timeout returns WAIT_TIMEOUT (258) if still running
        status = ctypes.windll.kernel32.WaitForSingleObject(handle, 0)
        ctypes.windll.kernel32.CloseHandle(handle)
        return status == 258
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def get_runtime_port_file() -> Path:
    return Path(get_data_dir("sd-server")) / "server_runtime.json"

def get_active_server_url(host: str = "127.0.0.1") -> Optional[str]:
    port_file = get_runtime_port_file()
    if not port_file.exists():
        return None
    try:
        data = json.loads(port_file.read_text(encoding="utf-8"))
        pid = data.get("pid")
        port = data.get("port")
        if isinstance(pid, int) and isinstance(port, int) and _is_pid_alive(pid):
            return f"http://{host}:{port}"
    except Exception:
        pass
    return None