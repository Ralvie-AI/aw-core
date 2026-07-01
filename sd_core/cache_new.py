import os
import subprocess
import logging
import json
import ctypes
from ctypes import wintypes

from sd_core.salt_file import MY_SALT
from cachetools import TTLCache

from sd_core.os_util import is_macos
from sd_core.const import CACHE_KEY, LOGGING_VERBOSE, PROFILE_FILE

IS_MACOS = is_macos()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the Windows Cryptographic API DLL
crypt32 = ctypes.windll.crypt32

logger = logging.getLogger(__name__)

class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte))
    ]


# Initialize a cache with a maximum size and a TTL (time-to-live)
# credentials_cache = TTLCache(maxsize=10, ttl=21600)     # 6 hours
credentials_cache = TTLCache(maxsize=1, ttl=1800)     # 1 hour


def encrypt_json(data: dict) -> bytes:
    json_bytes = json.dumps(data).encode("utf-8")
    salt_bytes = MY_SALT.encode("utf-8")

    blob_in = DATA_BLOB(
        len(json_bytes),
        ctypes.cast(
            ctypes.create_string_buffer(json_bytes),
            ctypes.POINTER(ctypes.c_byte),
        ),
    )

    blob_salt = DATA_BLOB(
        len(salt_bytes),
        ctypes.cast(
            ctypes.create_string_buffer(salt_bytes),
            ctypes.POINTER(ctypes.c_byte),
        ),
    )

    blob_out = DATA_BLOB()

    success = crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,
        ctypes.byref(blob_salt),
        None,
        None,
        0x01,
        ctypes.byref(blob_out),
    )

    if not success:
        raise ctypes.WinError()

    try:
        return bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)

def decrypt_json(encrypted_bytes: bytes) -> dict:
    salt_bytes = MY_SALT.encode("utf-8")

    blob_in = DATA_BLOB(
        len(encrypted_bytes),
        ctypes.cast(
            ctypes.create_string_buffer(encrypted_bytes),
            ctypes.POINTER(ctypes.c_byte),
        ),
    )

    blob_salt = DATA_BLOB(
        len(salt_bytes),
        ctypes.cast(
            ctypes.create_string_buffer(salt_bytes),
            ctypes.POINTER(ctypes.c_byte),
        ),
    )

    blob_out = DATA_BLOB()

    success = crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        ctypes.byref(blob_salt),
        None,
        None,
        0x01,
        ctypes.byref(blob_out),
    )

    if not success:
        raise ctypes.WinError()

    try:
        plaintext = bytes(
            ctypes.string_at(blob_out.pbData, blob_out.cbData)
        )
        return json.loads(plaintext.decode("utf-8"))
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)

def run_keychain_command(command):
    """Run a command for macOS Keychain."""
    try:
        logger.info(f"Running keychain command: {' '.join(command)}")
        subprocess.run(command, check=True, text=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Keychain command failed. Error: {e}")
        return False
    

def add_password(service, password):
    """Add or update a password in the system's secure storage."""
    logger.info(f"Adding/updating password for service {service}.")

    credentials_cache.clear()

    if  not service in password.keys():
        password.update({service: True})
        
    password = json.dumps(password)
    
    if IS_MACOS:
        command = ['security', 'add-generic-password', '-s', service, '-a', service, '-w', password, '-U']
        return run_keychain_command(command)
    else:
        from sd_core.util import get_running_path
        from sd_core.secure import encrypt_json_to_file
        file_path = os.path.join(get_running_path(), PROFILE_FILE)
        encrypt_json_to_file(file_path, password)

def keychain_item_exists(service):
    """Check if a keychain item exists in the system's secure storage."""    
    if IS_MACOS:
        command = ['security', 'find-generic-password', '-s', service, '-a', service]
        return run_keychain_command(command)
    else:
        from sd_core.util import get_running_path
        file_secure = os.path.join(get_running_path(), PROFILE_FILE)
        if os.path.exists(file_secure):
            return True        
        else:
            logger.info(f"There is no keychain item exists for service {service}.")
            return False 

     
def delete_password(service):
    """Delete a password from the system's secure storage if it exists."""
    logger.info(f"Deleting password for service {service}.")

    credentials_cache.clear()

    if keychain_item_exists(service):
        if IS_MACOS:
            command = ['security', 'delete-generic-password', '-s', service, '-a', service]
            return "Success" if run_keychain_command(command) else "Failed"
        else:
            from sd_core.util import get_running_path
            file_secure = os.path.join(get_running_path(), PROFILE_FILE)
            if os.path.exists(file_secure):
                os.remove(file_secure)
            return "Success"
    else:
        logger.warning("Keychain item not found.")
        return "Keychain item not found" 

def get_password(service):    
    """Retrieve a password from the system's secure storage."""
    logger.info(f"Retrieving password for service {service}.")
    if IS_MACOS:
        command = ['security', 'find-generic-password', '-s', service, '-a', service, '-w']
        try:
            result = subprocess.run(command, check=True, text=True, capture_output=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    else:        
        from sd_core.util import get_running_path
        from sd_core.secure import decrypt_json_from_file
        file_secure = os.path.join(get_running_path(), PROFILE_FILE)
        if os.path.exists(file_secure):
            return decrypt_json_from_file(file_secure)
        return None 


def store_credentials(service, credentials):
    """Store a service's credentials in the cache."""
    # credentials_cache[service] = credentials
    credentials_cache[service] = encrypt_json(credentials)

def get_credentials(service):
    """Retrieve a service's credentials from the cache."""
    # return credentials_cache.get(service)
    encrypted = credentials_cache.get(service)
    if encrypted is None:
        return None
    return decrypt_json(encrypted)

def clear_credentials(service):
    """Clear a service's credentials from the cache."""
    if service in credentials_cache:
        logger.info(f"Clearing credentials from cache for service: {service}")
        del credentials_cache[service]
    else:
        logger.info(f"No credentials found in cache for service: {service}")


def clear_all_credentials():
    """Clear all credentials from the cache."""
    logger.info("Clearing all credentials from cache.")
    credentials_cache.clear()


def cache_user_credentials(service):
    """Cache user credentials for the given service."""
    cached_credentials = get_credentials(service)

    # if LOGGING_VERBOSE == 1:
    #     logger.info(f"cached_credentials => {cached_credentials}")

    if cached_credentials is None:
        credentials_str = get_password(service)

        # if LOGGING_VERBOSE == 1:
        #     logger.info(f"credentials_str => {credentials_str}")

        if credentials_str:
            try:
                # Parse the JSON string to a dictionary
                credentials = json.loads(credentials_str)
                store_credentials(service, credentials)
                return credentials
            except json.JSONDecodeError:
                logger.error("Error decoding credentials from JSON.")
                return None
        else:
            logger.warning(f"No credentials found for service {service}.")
            return None
    else:
        return cached_credentials


def credentials():
    creds = cache_user_credentials(CACHE_KEY)
    credentials_cache.clear()
    return creds