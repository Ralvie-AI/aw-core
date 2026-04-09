import os 

# DEVELOPMENT_MODE = 0 is for local development.
# DEVELOPMENT_MODE = 1 is for production.

DEVELOPMENT_MODE = 1
STAGING = 1
INTERNAL = 0
LOGGING_VERBOSE = 0
CACHE_KEY = "Sundial"

PUBLIC_KEY = os.path.join(os.environ['LOCALAPPDATA'], 'Sundial', 'Sundial', 'sd-server', '{email}-{company_id}-public.pem')