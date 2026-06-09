import os 

# DEVELOPMENT_MODE = 0 is for local development.
# DEVELOPMENT_MODE = 1 is for production.

DEVELOPMENT_MODE = 1
STAGING = 1
INTERNAL = 0
LOGGING_VERBOSE = 1     # to log verbose set 1
CACHE_KEY = "Sundial"
SETTINGS_CACHE_KEY = "settings_cache"
LOCAL_HOST = "http://localhost:7600/api"

SYNC_TIME = 600 # 10 minutes
SCREEN_SHOT_SYNC_TIME = 60 # 1  minutes
STATUS_SYNC_TIME = 180 # 3 minutes
STATUS_SYNC_FIRST_TIME = 30 # 3 seconds


MAX_RETRIES = 3
DELAY_SECONDS = 3  # wait before retry

# 1 set up for configurable server setting
# 0 not set up for configurable server setting
CONFIG_SERVER = 0

PUBLIC_KEY = os.path.join(os.environ['LOCALAPPDATA'], 'Sundial', 'Sundial', 'sd-server', '{email}-{company_id}-public.pem')
HOST_TO_UPLOAD_SHOT_GET = "{protocol}://{host}/web/events/screenshot?fileFormat=json&userId={user_id}&companyId={company_id}"
