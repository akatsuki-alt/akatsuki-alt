from api import app
# Register API routes
from api import v1

import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4269)