from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Dict, List

from utils.logger import get_logger

logger = get_logger("cleaner")


class DataCleaner:
    def enrich(self, site_cfg: Dict, items: List[Dict]) -> List[Dict]:
        """
        Add timestamps, normalize whitespace, and propagate site metadata.
        """
        now = datetime.utcnow().isoformat()
        meta = site_cfg.get("metadata", {}) or {}

        for r in items:
            if "timestamp" not in r:
                r["timestamp"] = now
            # Normalize whitespace
            for k, v in list(r.items()):
                if isinstance(v, str):
                    r[k] = " ".join(v.split())
            # Propagate metadata
            for mk, mv in meta.items():
                if mk not in r:
                    r[mk] = mv
        return items

    def deduplicate(self, items: List[Dict], key_fields: List[str]) -> List[Dict]:
        """
        Remove duplicates based on a hash of key fields.
        """
        seen = set()
        unique = []
        for r in items:
            key = "|".join(str(r.get(k, "")).lower() for k in key_fields)
            digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            unique.append(r)
        logger.debug(f"Deduplicated from {len(items)} to {len(unique)}")
        return unique
