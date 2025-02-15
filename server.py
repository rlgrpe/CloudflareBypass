import asyncio
import os
import re
from contextlib import asynccontextmanager
from typing import Dict
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from client import CloudflareBypasser

SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))
os.environ.setdefault("TERM", "xterm-256color")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic (if any) ---
    yield
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
                # Optionally log other exceptions
                print("Task finished with exception:", result)


app = FastAPI(lifespan=lifespan)


class CookieResponse(BaseModel):
    cookies: Dict[str, str]
    user_agent: str


def is_safe_url(url: str) -> bool:
    parsed_url = urlparse(url)
    ip_pattern = re.compile(
        r"^(127\.0\.0\.1|localhost|0\.0\.0\.0|::1|10\.\d+\.\d+\.\d+|172\.1[6-9]\.\d+\.\d+|172\.2[0-9]\.\d+\.\d+|172\.3[0-1]\.\d+\.\d+|192\.168\.\d+\.\d+)$"
    )
    hostname = parsed_url.hostname
    if (hostname and ip_pattern.match(hostname)) or parsed_url.scheme == "file":
        return False
    return True


@app.get("/cookies", response_model=CookieResponse)
async def get_cookies(url: str, retries: int = 5, proxy: str = None):
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        driver = CloudflareBypasser(proxy, url, max_retries=retries)
        user_agent, cookies = await asyncio.to_thread(driver.bypass)
        cookies = {cookie.get("name", ""): cookie.get("value", " ") for cookie in cookies}
        return CookieResponse(cookies=cookies, user_agent=user_agent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
