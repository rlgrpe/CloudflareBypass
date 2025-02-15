import sys

from seleniumbase import SB, BaseCase

sys.argv.append("-n")


class CloudflareBypasser:
    def __init__(self, proxy: str | None, url: str, max_retries=5, log=True):
        self.proxy = proxy
        self.url = url
        self.max_retries = max_retries
        self.log = log

    def log_message(self, message):
        if self.log:
            print(message)

    def is_bypassed(self, sb: BaseCase):
        try:
            title = str(sb.get_title()).lower()
            return "just a moment" not in title
        except Exception as e:
            self.log_message(f"Error checking page title: {e}")
            return False

    def bypass(self):
        try_count = 0

        with SB(uc=True, proxy=self.proxy, xvfb=True) as sb:
            sb.activate_cdp_mode(self.url)

            while not self.is_bypassed(sb):
                if 0 < self.max_retries + 1 <= try_count:
                    self.log_message("Exceeded maximum retries. Bypass failed.")
                    break

                self.log_message(f"Attempt {try_count + 1}: Verification page detected. Trying to bypass...")

                try:
                    sb.uc_gui_click_captcha()
                except Exception as e:
                    self.log_message(f"{e}")

                try_count += 1
                sb.sleep(2)

                if self.is_bypassed(sb):
                    self.log_message("Bypass successful.")
                    return sb.get_user_agent(), sb.get_cookies()
                else:
                    self.log_message("Bypass failed.")
