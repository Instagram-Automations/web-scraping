from __future__ import annotations

from typing import Dict, List

from bs4 import BeautifulSoup

from utils.logger import get_logger

logger = get_logger("parser")


class ItemParser:
    def parse_page(self, site_cfg: Dict, page) -> List[Dict]:
        """
        Parse a single HTML page into item dicts based on selectors in site_cfg.
        """
        items: List[Dict] = []
        html = page.html or ""
        soup = BeautifulSoup(html, "lxml")

        item_selector = site_cfg.get("item_selector") or "body"
        containers = soup.select(item_selector)
        if not containers:
            logger.debug("No containers found; falling back to whole document")
            containers = [soup]

        fields_cfg: Dict = site_cfg.get("fields", {})
        for container in containers:
            record: Dict = {}
            for out_field, cfg in fields_cfg.items():
                selector = cfg.get("selector")
                attr = (cfg.get("attr") or "text").lower()
                optional = bool(cfg.get("optional", False))
                value = None

                try:
                    node = container.select_one(selector) if selector else None
                    if node:
                        if attr == "text":
                            value = node.get_text(strip=True)
                        else:
                            value = node.get(attr)
                except Exception as e:
                    if not optional:
                        logger.debug(f"Field extraction error for {out_field}: {e}")

                if value is None and not optional:
                    value = ""  # ensure field presence for non-optional
                if value is not None:
                    record[out_field] = value

            if record:
                items.append(record)

        # Attach source metadata if available
        meta = site_cfg.get("metadata", {})
        for r in items:
            if "source" not in r and "source" in meta:
                r["source"] = meta["source"]
        return items
