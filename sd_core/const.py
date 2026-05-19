import os 

# DEVELOPMENT_MODE = 0 is for local development.
# DEVELOPMENT_MODE = 1 is for production.

DEVELOPMENT_MODE = 1
STAGING = 1
INTERNAL = 0
LOGGING_VERBOSE = 0
CACHE_KEY = "Sundial"
SETTINGS_CACHE_KEY = "settings_cache"
LOCAL_HOST = "http://localhost:7600/api"



# 1 set up for configurable server setting
# 0 not set up for configurable server setting
CONFIG_SERVER = 0

PUBLIC_KEY = os.path.join(os.environ['LOCALAPPDATA'], 'Sundial', 'Sundial', 'sd-server', '{email}-{company_id}-public.pem')