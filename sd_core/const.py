
import os 

TIME_OUT = 60
TMP_VERSION = "1.3.5"

PIPE_NAME = r'\\.\pipe\AppSocket'

# DEVELOPMENT_MODE = 0 is for local development.
# DEVELOPMENT_MODE = 1 is for production.
DEVELOPMENT_MODE = 0
STAGING = 1

INTERNAL = 0
FORCE_VERBOSE = True     # True = dev / False = producton

CACHE_KEY = "Sundial"
SETTINGS_CACHE_KEY = "settings_cache"
LOCAL_HOST = "http://localhost:7600/api"

LOG_CLEAR_TIME = 180 #the days to clear old logs

SYNC_TIME = 600 # 10 minutes
SCREEN_SHOT_SYNC_TIME = 60 # 1  minutes
STATUS_SYNC_TIME = 180 # 3 minutes
STATUS_SYNC_FIRST_TIME = 30 # 30 seconds

MAX_RETRIES = 3
DELAY_SECONDS = 3  # wait before retry

# 1 set up for configurable server setting
# 0 not set up for configurable server setting
CONFIG_SERVER = 0

PUBLIC_KEY = os.path.join(os.path.expanduser("~"),
                "Library", "Application Support", "Sundial", "sd-server", '{email}-{company_id}-public.pem')
HOST_TO_UPLOAD_SHOT_GET = "{protocol}://{host}/web/events/screenshot?fileFormat=json&userId={user_id}&companyId={company_id}"