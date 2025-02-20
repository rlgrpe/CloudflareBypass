import logging
import sys

from seleniumbase import SB, BaseCase

sys.argv.append("-n")

logger = logging.getLogger("myapp")


class CloudflareBypasser:
    def __init__(self, proxy: str | None, url: str, max_retries=5, log=True, request_id: str = None):
        self.proxy = proxy
        self.url = url
        self.max_retries = max_retries
        self.log = log
        self.request_id = request_id or "N/A"

    def log_message(self, level, message):
        if self.log:
            logger.log(level=level, msg=f"[{self.request_id}] {message}")

    def is_bypassed(self, sb: BaseCase):
        try:
            title = str(sb.get_title()).lower()
            return "just a moment" not in title
        except Exception as e:
            self.log_message(logging.ERROR, f"Error checking page title: {e}")
            return False

    def bypass(self):
        try_count = 0

        with SB(uc=True, proxy=self.proxy, multi_proxy=True, xvfb=True) as sb:
            sb.activate_cdp_mode(self.url)

            while not self.is_bypassed(sb):
                if 0 < self.max_retries <= try_count:
                    self.log_message(logging.WARN, "Exceeded maximum retries. Bypass failed.")
                    break

                self.log_message(logging.INFO,
                                 f"Attempt {try_count + 1}: Verification page detected. Trying to bypass...")

                try:
                    sb.uc_gui_click_captcha()
                except Exception as e:
                    self.log_message(logging.ERROR, f"Captcha click error: {e}")

                try_count += 1
                sb.sleep(2)

                if self.is_bypassed(sb):
                    self.log_message(logging.INFO, "Bypass successful.")
                    return sb.get_user_agent(), sb.get_cookies()
                else:
                    self.log_message(logging.INFO, "Bypass attempt failed, retrying...")

        # Optionally, if the bypass never succeeded, raise an exception.
        raise Exception("Failed to bypass Cloudflare protection after maximum retries.")
