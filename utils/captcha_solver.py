from __future__ import annotations


class CaptchaDetected(Exception):
    """Raised when a likely CAPTCHA is detected on a page."""
    pass


CAPTCHA_HINTS = [
    "are you a human",
    "verify you are a human",
    "enter the characters you see",
    "recaptcha",
    "hcaptcha",
    "cloudflare turnstile",
    "unusual traffic",
]


def maybe_detect_captcha(html: str) -> None:
    """
    Lightweight detector for common CAPTCHA phrases.
    """
    if not html:
        return
    low = html.lower()
    if any(hint in low for hint in CAPTCHA_HINTS):
        raise CaptchaDetected("Possible CAPTCHA encountered.")
