import os
import base64
import ctypes
import sys
import logging
import threading
import time
import subprocess
from datetime import datetime, timedelta
from typing import Tuple

import requests
from cryptography.fernet import Fernet
import keyring
import pam

from sd_core.cache import cache_user_credentials, delete_password, clear_credentials
from sd_core.const import CACHE_KEY, DEVELOPMENT_MODE, LOGGING_VERBOSE

os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

logger = logging.getLogger(__name__)


class VersionException(Exception):
    ...


def _version_info_tuple() -> Tuple[int, int, int]:  # pragma: no cover
    """
     Return major minor micro versions of Python. This is useful for detecting version changes in Python and to avoid having to re - evaluate the code every time it is called.


     @return tuple of major minor micro versions of Python ( int ) or ( int int int ) depending on the
    """
    return (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)


def assert_version(required_version: Tuple[int, ...] = (3, 5)):  # pragma: no cover
    """
     Assert that the version of Python is at least the required version. This is useful for debugging and to ensure that you don't accidentally run a program that is incompatible with the version you are running.

     @param required_version - The minimum version required to run the
    """
    actual_version = _version_info_tuple()
    # If the Python version is less than required_version
    if actual_version <= required_version:
        raise VersionException(
            (
                "Python version {} not supported, you need to upgrade your Python"
                + " version to at least {}."
            ).format(required_version)
        )
    logger.debug(f"Python version: {_version_info_tuple()}")


def generate_key(service_name, user_name):
    """
     Generate a key and store it in the keyring. This is a convenience method for testing. You should use : func : ` Fernet. generate_key ` instead of this method if you don't want to use the key generation functionality.

     @param service_name - The name of the service that will be used for the key generation.
     @param user_name - The name of the user that will be used for the key generation
    """
    key = Fernet.generate_key()
    key_string = base64.urlsafe_b64encode(key).decode('utf-8')
    keyring.set_password(service_name, user_name, key_string)


# Load the secret key from a file
def load_key(service_name):
    """
     Load key from cache. This is used to cache credentials that are stored in Sundial_KEY_FILE

     @param service_name - Name of the service we are looking up

     @return A dict of credentials or None if not found in the cache or no credentials could be found in the
    """
    cached_credentials = cache_user_credentials(CACHE_KEY)
    # Returns the credentials for the service.
    if cached_credentials != None:
        return cached_credentials.get(service_name)
    else:
        return None


def str_to_fernet(key):
    """
     Convert a FERNET key to a string. This is used to decrypt keys that are stored in the database.

     @param key - The key to convert. Must be a string.

     @return The base64 - encoded key as a string. If the key is invalid it will be returned as None
    """
    return base64.urlsafe_b64decode(key.encode('utf-8'))


# Encrypt the UUID
def encrypt_uuid(uuid_str, key):
    """
     Encrypt UUID and return it as Base64 encoded string. This is useful for storing UUIDs in DB

     @param uuid_str - UUID to be encrypted.
     @param key - Fernet key to use for encryption. Must be able to decrypt UUIDs.

     @return Base64 encoded UUID or None if encryption failed for any reason ( in which case exception is logged at log level
    """
    try:
        fernet = Fernet(key)
        encrypted_uuid = fernet.encrypt(str(uuid_str).encode())
        return base64.urlsafe_b64encode(encrypted_uuid).decode('utf-8')
    except Exception as e:
        print(f"encrypt_uuid error: {e}")
        return None


# Decrypt the UUID
def decrypt_uuid(encrypted_uuid, key):
    """
     Decrypt UUID and return it. This function is used to decrypt UUID with Fernet. If decryption fails None is returned

     @param encrypted_uuid - encrypted UUID as base64 encoded string
     @param key - key to use for decryption. Must be able to decrypt UUID

     @return decrypted UUID or None if decryption failed ( in which case user is reset to default state ) >>> decrypt_uuid ('abc123 '
    """
    try:
        fernet = Fernet(key)
        encrypted_uuid_byte = base64.urlsafe_b64decode(
            encrypted_uuid.encode('utf-8'))
        decrypted_uuid = fernet.decrypt(encrypted_uuid_byte)
        return decrypted_uuid.decode()
    except Exception as e:
        reset_user()
        print(f"decrypt_uuid error: {e}")
        return None


def authenticate(username, password):
    """
     Authenticate a user against the system. This is a wrapper around L { authenticateWindows } or L { authenticateMac } depending on the platform.

     @param username - The username to authenticate with. If this is None the user will be prompted for one.
     @param password - The password to authenticate with. If this is None the user will be prompted for one.

     @return A tuple of ( success_code response ) where success_code is 0 if the user is authenticated successfully and response is the response from the server
    """
    # Authenticate with the user s username and password.
    if sys.platform != "darwin":
        return authenticateWindows(username=username, password=password)
    else:
        return authenticateMac(username=username, password=password)


def authenticateWindows(username, password):
    """
     Authenticate using Windows Logon API. This is a low - level function to use for authenticating a user.

     @param username - Username of the user to authenticate. If this is None the user will be prompted for one.
     @param password - Password of the user to authenticate. If this is None the user will be prompted for one.

     @return True if authentication was successful False otherwise. >>> authenticateWindows ('John Doe'' Password')
    """
    try:
        handle = ctypes.windll.advapi32.LogonUserW(
            username,
            None,
            password,
            2,  # LOGON32_LOGON_NETWORK
            0,  # LOGON32_PROVIDER_DEFAULT
            ctypes.byref(ctypes.c_void_p())
        )
        # Close the handle and return True if successful.
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        else:
            return False
    except Exception as e:
        print(f"Authentication error: {e}")
        return False


def authenticateMac(username, password):
    """
     Authenticates a mac user based on username and password. This is a wrapper around pam. authenticate to catch errors that occur during authentication

     @param username - The username to authenticate with
     @param password - The password to authenticate with ( can be empty )

     @return True if authentication was successful False if not ( or PAMError was raised ). The return value is a boolean
    """
    try:
        # Attempt to authenticate the user with the provided username and password
        # Returns true if the user is authenticated and password is valid.
        if pam.authenticate(username, password):
            return True
        else:
            return False
    except pam.PAMError as e:
        print(f"Authentication error: {e}")
        return False


def reset_user():
    """
     Reset user to default values and stop all modules on success or failure Args : None Return : None Purpose : Clears password and cache
    """
    try:
        delete_password(CACHE_KEY)
        clear_credentials(CACHE_KEY)
        # stop_all_module()
    except Exception as e:
        print(f"Authentication error: {e}")

def is_internet_connected():
    """
     Checks if we can connect to the internet. This is a helper function for get_internet_connected


     @return True if we can connect to
    """
    try:
        # Try making a simple HTTP GET request to a well-known website
        response = requests.get("http://www.bing.com")
        # If the request is successful, return True
        return response.status_code == 200
    except requests.ConnectionError:
        # If there's a connection error, return False
        return False


def get_domain(url):
    if not url:
        return url
    url = url.replace("https://", "").replace("http://",
                                              "").replace("www.", "")
    parts = url.split("/")
    domain_parts = parts[0].split(".")

    if len(domain_parts) > 2:
        return f'{domain_parts[0]} - {domain_parts[1]}'
    elif len(domain_parts) == 2:
        return domain_parts[0]
    else:
        return parts[0]


def get_document_title(event):
    url = event.data.get('url', '')
    title = event.data.get('title', '')
    if "sharepoint.com" in url:
        title = "OneDrive"
    return title


def remove_more_page_suffix(text):
    # Check if "More Page" string exists in the text
    if "more page" in text.lower():
        # Split the text at "And"
        words = text.split("and")
        # Return the first element
        return words[0].strip()
    else:
        return text

def get_running_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def _task_runner(exec_cmd, timeout_sec):
    # logger.info(f"Starting module {exec_cmd}")
    if not isinstance(exec_cmd, list):
        exec_cmd = [exec_cmd]

    logger.debug("Running: {}".format(exec_cmd))

    # Don't display a console window on Windows
    # See: https://github.com/ActivityWatch/activitywatch/issues/212
    startupinfo = None
    if sys.platform in ("win32", "cygwin"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        # Use the 'with' statement to ensure underlying handles are cleaned up even if exceptions occur
        with subprocess.Popen(
                exec_cmd,
                universal_newlines=True,
                startupinfo=startupinfo
        ) as proc:

            try:
                # Block and wait, with a timeout mechanism to prevent the process accumulation
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                # If the exe hangs, force kill it to prevent processes from piling up!
                logger.error(f"Task execution timed out ({timeout_sec}s)! Force cleaning up...")
                proc.kill()
                proc.wait()
    except Exception as e:
        logger.error(f"Unexpected error occurred while starting the process: {e}")

def start_exe(exec_cmd, timeout_sec=None):
    logger.info(f"Starting module start exe {exec_cmd}")
    worker_thread = threading.Thread(
        target=_task_runner,
        args=(exec_cmd, timeout_sec),
        daemon=True
    )
    worker_thread.start()
    return worker_thread


def stop_process_by_exe(exe_name, time_sleep=0.2):
    if DEVELOPMENT_MODE == LOGGING_VERBOSE:
        logger.info(f"killing start cmd_name {exe_name}")   
    subprocess.run(f"taskkill /F /IM {exe_name}", shell=True)
    time.sleep(time_sleep)  # wait 200ms for process cleanup


def convert_datetime_string(dt_string: str) -> str:
    from dateutil import parser
    from zoneinfo import ZoneInfo

    dt = parser.parse(dt_string)
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

def add_end_time(start_time, seconds_to_add):
    # Parse the ISO string
    dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
    # Add seconds
    new_dt = dt + timedelta(seconds=seconds_to_add)

    # Convert back to ISO8601 with 'Z'
    # end_time = new_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    # Round to nearest second
    rounded_dt = new_dt.replace(microsecond=0)
    if new_dt.microsecond >= 500_000:
        rounded_dt += timedelta(seconds=1)

    # Format as ISO8601 without fractional seconds
    end_time = rounded_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return end_time
