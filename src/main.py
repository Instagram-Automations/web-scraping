import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

from utils.logger import get_logger
from utils.proxy_manager import ProxyManager
from scraper import WebScraper
from parser import ItemParser
from cleaner import DataCleaner
from exporter import DataExporter

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = APP_ROOT / "config" / "sites.yaml"
DEFAULT_OUTDIR = APP_ROOT / "output"
DEFAULT_RAWDIR = APP_ROOT / "data" / "raw"
DEFAULT_PROCDIR = APP_ROOT / "data" / "processed"
DEFAULT_PROXIES = APP_ROOT / "config" / "proxies.json"
DEFAULT_UA_FILE = APP_ROOT / "config" / "user_agents.txt"


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs(*paths: Path):
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Multi-Website Scraping Service")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG), help="Path to sites.yaml")
    parser.add_argument("--outdir", type=str, default=str(DEFAULT_OUTDIR), help="Directory for final outputs")
    parser.add_argument("--rawdir", type=str, default=str(DEFAULT_RAWDIR), help="Directory for raw HTML dumps")
    parser.add_argument("--procdir", type=str, default=str(DEFAULT_PROCDIR), help="Directory for processed JSON")
    parser.add_argument("--limit", type=int, default=0, help="Max items per site (0 = no limit)")
    parser.add_argument("--timeout", type=int, default=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")), help="Request timeout seconds")
    parser.add_argument("--retries", type=int, default=int(os.getenv("MAX_RETRIES", "3")), help="Max HTTP retries per URL")
    parser.add_argument("--proxies", type=str, default=str(DEFAULT_PROXIES), help="Path to proxies.json")
    parser.add_argument("--ua-file", type=str, default=str(DEFAULT_UA_FILE), help="Path to user_agents.txt")
    args = parser.parse_args()

    logger = get_logger("runner")

    cfg = load_config(Path(args.config))
    ensure_dirs(Path(args.outdir), Path(args.rawdir), Path(args.procdir))

    proxy_mgr = ProxyManager(Path(args.proxies))
    scraper = WebScraper(timeout=args.timeout, retries=args.retries, proxy_manager=proxy_mgr, ua_file=Path(args.ua_file))
    parser_mod = ItemParser()
    cleaner = DataCleaner()
    exporter = DataExporter(Path(args.outdir), Path(args.rawdir), Path(args.procdir))

    all_items = []
    job_started = datetime.utcnow().isoformat()

    for site in cfg.get("sites", []):
        site_name = site.get("name", "unnamed")
        logger.info(f"==> Processing site: {site_name}")
        items_for_site = []

        raw_pages = scraper.crawl_site(site, raw_dir=Path(args.rawdir))
        for page in raw_pages:
            parsed = parser_mod.parse_page(site, page)
            if args.limit and len(parsed) > args.limit:
                parsed = parsed[: args.limit]
            items_for_site.extend(parsed)

        # Enrich & clean
        items_for_site = cleaner.enrich(site, items_for_site)
        items_for_site = cleaner.deduplicate(items_for_site, key_fields=["title", "url"])
        logger.info(f"[{site_name}] Parsed {len(items_for_site)} items")

        # Export per-site artifacts
        exporter.save_site_json(site_name, items_for_site)
        all_items.extend(items_for_site)

    # Export combined outputs
    exporter.save_combined("results.json", all_items)
    exporter.save_combined_csv("results.csv", all_items)

    # Also store a compact manifest
    manifest = {
        "job_started": job_started,
        "job_finished": datetime.utcnow().isoformat(),
        "site_count": len(cfg.get("sites", [])),
        "total_items": len(all_items),
    }
    with open(Path(args.outdir) / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Print summary table to stdout
    if all_items:
        df = pd.DataFrame(all_items)
        keep_cols = [c for c in ["title", "url", "price", "description", "source", "timestamp"] if c in df.columns]
        print(df[keep_cols].head(20).to_string(index=False))
    else:
        logger.warning("No items extracted. Check configuration, connectivity, or selectors.")


if __name__ == "__main__":
    main()
