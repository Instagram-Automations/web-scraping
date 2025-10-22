from __future__ import annotations

import json
from itertools import cycle
from pathlib import Path
from typing import Optional

from .logger import get_logger

logger = get_logger("proxy")


class ProxyManager:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self._iterator = None
        self._load()

    def _load(self) -> None:
        proxies = []
        mode = "round_robin"
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                proxies = cfg.get("proxies", []) or []
                mode = cfg.get("mode", "round_robin")
        except Exception as e:
            logger.info(f"No proxies loaded ({e}); continuing without proxies.")
        self.mode = mode
        self.proxies = proxies
        self._iterator = cycle(self.proxies) if self.proxies else None

    def next_proxy(self) -> Optional[str]:
        if not self._iterator:
            return None
        return next(self._iterator)
