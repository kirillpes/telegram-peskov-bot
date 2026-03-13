"""
migrate_users.py — Import users from CutKaty_Subs.csv into PostgreSQL.

CSV columns: date, user_id, user_name, tarif, gens_left, gens_count, easter_egg1

Usage:
    python migrate_users.py CutKaty_Subs.csv
"""

import asyncio
import csv
import logging
import sys
from pathlib import Path

import database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def migrate(csv_path: str):
    path = Path(csv_path)
    if not path.exists():
        logger.error(f"File not found: {csv_path}")
        sys.exit(1)

    await database.init_db()

    inserted = 0
    skipped = 0
    errors = 0
    seen_ids = set()  # deduplicate (CSV has duplicate stlv_93)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            row = {k.lower().strip(): (v or "").strip() for k, v in row.items()}

            raw_id = row.get("user_id", "")
            if not raw_id or not raw_id.lstrip("-").isdigit():
                skipped += 1
                continue

            tg_id = int(raw_id)

            if tg_id in seen_ids:
                logger.info(f"Row {row_num}: duplicate user_id {tg_id}, skipping")
                skipped += 1
                continue
            seen_ids.add(tg_id)

            username = row.get("user_name") or None
            raw_gens = row.get("gens_count", "0")
            try:
                gens_count = int(raw_gens) if raw_gens else 0
            except ValueError:
                gens_count = 0

            easter_egg1 = row.get("easter_egg1", "").lower() in ("yes", "1", "true")

            try:
                await database.upsert_user_from_csv(
                    tg_id=tg_id,
                    username=username,
                    gens_count=gens_count,
                    easter_egg1=easter_egg1,
                )
                logger.info(f"Row {row_num}: upserted {tg_id} (@{username}) gens={gens_count}")
                inserted += 1
            except Exception as e:
                logger.error(f"Row {row_num}: failed to upsert {tg_id}: {e}")
                errors += 1

    await database.close_pool()

    logger.info(
        f"\n=== Migration complete ===\n"
        f"Inserted/updated: {inserted}\n"
        f"Skipped:          {skipped}\n"
        f"Errors:           {errors}"
    )


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "CutKaty_Subs.csv"
    asyncio.run(migrate(csv_path))


if __name__ == "__main__":
    main()
