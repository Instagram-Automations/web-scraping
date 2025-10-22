from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from utils.logger import get_logger
from utils.proxy_manager import ProxyManager
from utils.captcha_solver import CaptchaDetected, maybe_detect_captcha


@dataclass
class Page:
    url: str
    html: str
    status_code: int
    meta: Dict


class WebScraper:
    def __init__(
        self,
        timeout: int = 20,
        retries: int = 3,
        proxy_manager: Optional[ProxyManager] = None,
        ua_file: Optional[Path] = None,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.proxy_manager = proxy_manager
        self.logger = get_logger("scraper")
        self.user_agents = self._load_user_agents(ua_file) if ua_file else []

    def _load_user_agents(self, path: Path) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            if not lines:
                self.logger.warning("User agent file is empty.")
            return lines
        except Exception as e:
            self.logger.warning(f"Failed to load user agents from {path}: {e}")
            return []

    def _headers(self, site_cfg: Dict) -> Dict[str, str]:
        base = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        }
        if self.user_agents:
            base["User-Agent"] = random.choice(self.user_agents)
        # Merge site-specific headers
        request_cfg = site_cfg.get("request", {})
        return {**base, **request_cfg.get("headers", {})}

    def _proxies(self) -> Optional[Dict[str, str]]:
        if not self.proxy_manager:
            return None
        proxy = self.proxy_manager.next_proxy()
        if not proxy:
            return None
        return {"http": proxy, "https": proxy}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((requests.RequestException, CaptchaDetected)),
        reraise=True,
    )
    def fetch(self, url: str, headers: Dict[str, str], cookies: Optional[Dict] = None) -> Page:
        proxies = self._proxies()
        resp = requests.get(url, headers=headers, cookies=cookies or {}, proxies=proxies, timeout=self.timeout)
        html = resp.text or ""
        maybe_detect_captcha(html)  # may raise CaptchaDetected to trigger retry
        return Page(url=url, html=html, status_code=resp.status_code, meta={"proxies": proxies or {}})

    def crawl_site(self, site_cfg: Dict, raw_dir: Path) -> Iterable[Page]:
        start_urls = site_cfg.get("start_urls", [])
        pagination = site_cfg.get("pagination", {}) or {}
        next_selector = pagination.get("next_selector", "")
        max_pages = int(pagination.get("max_pages", 1))
        cookies = (site_cfg.get("request") or {}).get("cookies", {})

        headers = self._headers(site_cfg)
        pages: List[Page] = []

        for start in start_urls:
            current_url = start
            page_count = 0

            while current_url and page_count < max_pages:
                page_count += 1
                try:
                    if current_url.startswith("file://"):
                        # Offline fallback page for demo/offline environments
                        html = "<html><body><div class='card'><h2 class='title'>Offline Item</h2><span class='price'>$0.00</span></div></body></html>"
                        page = Page(url=current_url, html=html, status_code=200, meta={"offline": True})
                    else:
                        page = self.fetch(current_url, headers=headers, cookies=cookies)
                    pages.append(page)
                    self._dump_raw(raw_dir, page, site_cfg.get("name", "site"))
                    self._sleep_jitter()

                    if not next_selector:
                        break

                    next_url = self._find_next(page.html, current_url, next_selector)
                    if not next_url or next_url == current_url:
                        break
                    current_url = next_url
                except CaptchaDetected:
                    self._sleep_backoff()
                    continue
                except requests.RequestException as e:
                    self.logger.warning(f"Request error at {current_url}: {e}")
                    break
                except Exception as e:
                    self.logger.exception(f"Unexpected error at {current_url}: {e}")
                    break

        return pages

    def _find_next(self, html: str, base_url: str, next_selector: str) -> Optional[str]:
        soup = BeautifulSoup(html, "lxml")
        el = soup.select_one(next_selector) if next_selector else None
        if not el:
            return None
        href = el.get("href") or el.get("data-href")
        if not href:
            return None
        return urljoin(base_url, href)

    def _dump_raw(self, raw_dir: Path, page: Page, site_name: str) -> None:
        site_dir = raw_dir / site_name
        site_dir.mkdir(parents=True, exist_ok=True)
        safe = page.url.replace("://", "_").replace("/", "_")
        path = site_dir / f"{safe}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(page.html)

    def _sleep_jitter(self):
        time.sleep(random.uniform(0.5, 1.5))

    def _sleep_backoff(self):
        time.sleep(random.uniform(3, 6))
