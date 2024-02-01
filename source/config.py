import os

POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"

OSSAPI_ID=""
OSSAPI_SECRET=""

def load_env():
    for k,v in os.environ.keys():
        if k in __dict__:
            __dict__[k] = v
