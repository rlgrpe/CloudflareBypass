# Cloudflare Turnstile Page Bypass

# Install

`pip install -r requirements.txt`

# Start

`python server.py`

# Usage

`curl --location 'http://localhost:8000/cookies?url=https%3A%2F%2Fgoogle.com%2F&proxy=user%3Apassword%401.1.1.1%3A8181&retries=5'`

Response:

```json
{
  "cookies": {
    "cf_clearance": "example"
  },
  "user_agent": "example"
}
```