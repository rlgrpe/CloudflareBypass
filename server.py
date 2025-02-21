import asyncio
import json
import logging.config
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Json

import logging_config
from client import CloudflareBypasser

SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))
os.environ.setdefault("TERM", "xterm-256color")

logger = logging.getLogger("myapp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic ---
    # Create a custom ThreadPoolExecutor with an increased max_workers value
    executor = ThreadPoolExecutor()
    loop = asyncio.get_running_loop()
    loop.set_default_executor(executor)

    try:
        yield
    finally:
        # --- Shutdown logic ---
        # Cancel all pending tasks except the current one
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            for task in tasks:
                task.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, asyncio.CancelledError):
                    continue  # Suppress cancellation errors
                elif isinstance(result, Exception):
                    logger.error("Task finished with exception: %s", result)
        executor.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


class CookieResponse(BaseModel):
    cookies: Json
    user_agent: str


def is_safe_url(url: str) -> bool:
    parsed_url = urlparse(url)
    ip_pattern = re.compile(
        r"^(127\.0\.0\.1|localhost|0\.0\.0\.0|::1|10\.\d+\.\d+\.\d+|"
        r"172\.1[6-9]\.\d+\.\d+|172\.2[0-9]\.\d+\.\d+|"
        r"172\.3[0-1]\.\d+\.\d+|192\.168\.\d+\.\d+)$"
    )
    hostname = parsed_url.hostname
    if (hostname and ip_pattern.match(hostname)) or parsed_url.scheme == "file":
        return False
    return True


# Middleware to log inbound and outbound requests, and attach a request ID.
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info(f"[{request_id}] Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"[{request_id}] Outgoing response: {response.status_code}")
    return response


@app.get("/cookies", response_model=CookieResponse)
async def get_cookies(request: Request, url: str, retries: int = 5, proxy: str = None):
    request_id = request.state.request_id
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        # Pass the request_id into the CloudflareBypasser for consistent logging.
        driver = CloudflareBypasser(proxy, url, max_retries=retries, request_id=request_id)
        # Run the blocking bypass method in a thread to allow concurrency.
        user_agent, cookies = await asyncio.to_thread(driver.bypass)
        cookies = json.dumps(cookies)
        return CookieResponse(cookies=cookies, user_agent=user_agent)
    except Exception as e:
        logger.error(f"[{request_id}] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, log_config=logging_config.LOGGING_CONFIG)
