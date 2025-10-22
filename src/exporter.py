from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict

import pandas as pd

from utils.logger import get_logger

logger = get_logger("exporter")


class DataExporter:
    def __init__(self, out_dir: Path, raw_dir: Path, proc_dir: Path) -> None:
        self.out_dir = out_dir
        self.raw_dir = raw_dir
        self.proc_dir = proc_dir
        for d in (self.out_dir, self.raw_dir, self.proc_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save_site_json(self, site_name: str, items: List[Dict]) -> None:
        site_path = self.proc_dir / f"{site_name}.json"
        with open(site_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        logger.info(f"Wrote {len(items)} items -> {site_path}")

    def save_combined(self, filename: str, items: List[Dict]) -> None:
        path = self.out_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        logger.info(f"Combined JSON saved -> {path}")

    def save_combined_csv(self, filename: str, items: List[Dict]) -> None:
        path = self.out_dir / filename
        if not items:
            # Create an empty CSV with common headers
            pd.DataFrame(columns=["title", "url", "price", "description", "source", "timestamp"]).to_csv(path, index=False)
            logger.info(f"Empty CSV scaffold saved -> {path}")
            return

        df = pd.DataFrame(items)
        # Order columns if present
        col_order = [c for c in ["title", "url", "price", "description", "category", "source", "timestamp"] if c in df.columns]
        others = [c for c in df.columns if c not in col_order]
        df = df[col_order + others]
        df.to_csv(path, index=False)
        logger.info(f"Combined CSV saved -> {path}")
