import json 
import logging
import ctypes
from ctypes import wintypes

# from sd_core.salt_file import MY_SALT
from sd_core import salt_file
# Load the Windows Cryptographic API DLL
crypt32 = ctypes.windll.crypt32

logger = logging.getLogger(__name__)

class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte))
    ]

def encrypt_json_to_file(filepath, data_dict):    
    """Serializes a dictionary to JSON, encrypts it with DPAPI using a salt, and saves to disk."""
    # 1. Convert the JSON object/dict into a UTF-8 byte array
    json_string = json.dumps(data_dict)
    json_bytes = json_string.encode('utf-8')
    
    # 2. Convert the Salt string into a byte array
    salt_bytes = salt_file.get_salt().encode('utf-8')
    # 3. Prepare C-structures for the target data and the salt (entropy)
    blob_in = DATA_BLOB(len(json_bytes), ctypes.cast(ctypes.create_string_buffer(json_bytes), ctypes.POINTER(ctypes.c_byte)))
    blob_salt = DATA_BLOB(len(salt_bytes), ctypes.cast(ctypes.create_string_buffer(salt_bytes), ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    
    # Flag 0x01 = CRYPTPROTECT_UI_FORBIDDEN (prevents OS dialog popups)
    success = crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,                 # Optional description string
        ctypes.byref(blob_salt), # Passing our salt here
        None,                 # Reserved
        None,                 # Optional prompt structure
        0x01,                 # Flags
        ctypes.byref(blob_out)
    )
    
    if not success:
        raise ctypes.WinError()
        
    try:
        # 4. Write the raw encrypted bytes to the file
        encrypted_bytes = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
        with open(filepath, 'wb') as f:
            f.write(encrypted_bytes)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)

def decrypt_json_from_file(filepath):
    """Reads a DPAPI .bin file, decrypts it using the provided salt, and returns the JSON dict."""
    # 1. Read the encrypted bytes from disk
    with open(filepath, 'rb') as f:
        encrypted_bytes = f.read()
        
    salt_bytes = salt_file.get_salt().encode('utf-8')
    
    blob_in = DATA_BLOB(len(encrypted_bytes), ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte)))
    blob_salt = DATA_BLOB(len(salt_bytes), ctypes.cast(ctypes.create_string_buffer(salt_bytes), ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    
    # 2. Decrypt passing the exact same salt structure
    success = crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        ctypes.byref(blob_salt), # Must match encryption salt exactly
        None,
        None,
        0x01,
        ctypes.byref(blob_out)
    )
    
    if not success:
        err = ctypes.WinError()
        logger.error("Failed to decrypt : %s", err)
        return None       

    try:
        # 3. Parse the decrypted bytes back into a Python dictionary
        decrypted_bytes = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
        json_string = decrypted_bytes.decode('utf-8')
        return json.loads(json_string)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)

# --- Verification Example ---
if __name__ == "__main__":
    # Your sensitive application state or configs
    config_data = {
        "app_id": "monitor_01",
        "api_key": "live_pk_51Nx82FkL9z...",
        "db_encryption_key": "sqlcipher_master_passphrase_xyz",        
    }   
    FILENAME = "secure_config.bin"
    
    # Encrypt and save
    encrypt_json_to_file(FILENAME, config_data)
    
    # Decrypt and parse back
    try:
        loaded_data = decrypt_json_from_file(FILENAME)
        print("\n[+] Decrypted Data Result:")
        print(json.dumps(loaded_data, indent=4))
    except Exception as err:
        print(f"[-] Error: {err}")
