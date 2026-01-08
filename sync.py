#!/usr/bin/env python3
"""
Sync Rize time tracking data to Exist.io custom attributes.

This script fetches time metrics from Rize and writes them to Exist.io
as custom attributes.

Usage:
    python sync.py           # Sync today's data
    python sync.py --setup   # First-time setup (create attributes)
    python sync.py --migrate # Migrate from old rize_* attributes to new names
"""
import argparse
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

from rize_client import get_all_daily_data
from exist_client import ExistClient


# Attribute configuration - clean names without service prefix
ATTRIBUTES = {
    # Duration attributes (value in minutes)
    "focus_time": {
        "label": "Focus time",
        "value_type": "duration",
        "group": "productivity",
    },
    "tracked_time": {
        "label": "Tracked time",
        "value_type": "duration",
        "group": "productivity",
    },
    "break_time": {
        "label": "Break time",
        "value_type": "duration",
        "group": "productivity",
    },
    "meeting_time": {
        "label": "Meeting time",
        "value_type": "duration",
        "group": "productivity",
    },
    "coding_time": {
        "label": "Coding time",
        "value_type": "duration",
        "group": "productivity",
    },
    "design_time": {
        "label": "Design time",
        "value_type": "duration",
        "group": "productivity",
    },
    # Count attributes (integer value)
    "focus_sessions": {
        "label": "Focus sessions",
        "value_type": "integer",
        "group": "productivity",
    },
}

# Old attributes to migrate from
OLD_ATTRIBUTES = ["rize_focus_time", "rize_tracked_time"]


def load_config() -> dict:
    """Load configuration from .env file."""
    load_dotenv()

    required = [
        "RIZE_API_KEY",
        "EXIST_ACCESS_TOKEN",
    ]
    optional = [
        "EXIST_REFRESH_TOKEN",
        "EXIST_CLIENT_ID",
        "EXIST_CLIENT_SECRET",
    ]

    config = {}
    missing = []

    for key in required:
        value = os.getenv(key)
        if not value:
            missing.append(key)
        config[key] = value

    for key in optional:
        config[key] = os.getenv(key)

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Please check your .env file")
        sys.exit(1)

    return config


def get_exist_client(config: dict) -> ExistClient:
    """Create an ExistClient from config."""
    return ExistClient(
        access_token=config["EXIST_ACCESS_TOKEN"],
        refresh_token=config.get("EXIST_REFRESH_TOKEN"),
        client_id=config.get("EXIST_CLIENT_ID"),
        client_secret=config.get("EXIST_CLIENT_SECRET"),
    )


def migrate_attributes(exist: ExistClient):
    """Release old rize_* attributes."""
    print("Migrating from old attribute names...")

    for attr_name in OLD_ATTRIBUTES:
        try:
            exist.release_attribute(attr_name)
            print(f"  Released: {attr_name}")
        except Exception as e:
            print(f"  Could not release {attr_name}: {e}")

    print("Migration complete. Now run --setup to create new attributes.")


def setup_attributes(exist: ExistClient):
    """Create and acquire the custom attributes in Exist."""
    print("Setting up Exist attributes...")

    # Check what attributes we already own
    try:
        owned = exist.get_owned_attributes()
        owned_names = {attr["attribute"] for attr in owned}
    except Exception as e:
        print(f"Warning: Could not fetch owned attributes: {e}")
        owned_names = set()

    for attr_name, attr_config in ATTRIBUTES.items():
        if attr_name in owned_names:
            print(f"  Already own: {attr_name}")
            continue

        # Try to create the attribute
        try:
            result = exist.create_attribute(
                label=attr_config["label"],
                value_type=attr_config["value_type"],
                group=attr_config["group"],
            )
            print(f"  Created: {attr_name}")

            if isinstance(result, list) and result:
                created = result[0]
                if "name" in created:
                    print(f"    -> {created['name']}")
                if "error" in created:
                    print(f"    -> Error: {created['error']}")

        except Exception as e:
            print(f"  Could not create {attr_name}: {e}")

        # Try to acquire ownership
        try:
            result = exist.acquire_attribute(attr_name)
            print(f"  Acquired: {attr_name}")
        except Exception as e:
            print(f"  Could not acquire {attr_name}: {e}")

    print("Setup complete!")


def sync_data(config: dict, target_date: date = None):
    """Sync Rize data to Exist for the given date."""
    if target_date is None:
        target_date = date.today()

    print(f"Syncing data for {target_date.isoformat()}...")

    # Fetch from Rize
    print("  Fetching from Rize...")
    try:
        rize_data = get_all_daily_data(config["RIZE_API_KEY"], target_date)
    except Exception as e:
        print(f"  Error fetching Rize data: {e}")
        return False

    # Convert seconds to minutes for duration attributes
    metrics = {
        "focus_time": rize_data["focus_time"] // 60,
        "tracked_time": rize_data["tracked_time"] // 60,
        "break_time": rize_data["break_time"] // 60,
        "meeting_time": rize_data["meeting_time"] // 60,
        "coding_time": rize_data["coding_time"] // 60,
        "design_time": rize_data["design_time"] // 60,
        "focus_sessions": rize_data["focus_sessions"],  # count, not duration
    }

    print(f"  Rize data:")
    print(f"    focus={metrics['focus_time']}min, tracked={metrics['tracked_time']}min")
    print(f"    break={metrics['break_time']}min, meeting={metrics['meeting_time']}min")
    print(f"    coding={metrics['coding_time']}min, design={metrics['design_time']}min")
    print(f"    focus_sessions={metrics['focus_sessions']}")

    # Update Exist
    exist = get_exist_client(config)

    print("  Updating Exist...")
    success_count = 0
    fail_count = 0

    for attr_name, value in metrics.items():
        try:
            result = exist.update_attribute(attr_name, target_date, value)
            if result.get("success"):
                success_count += 1
            elif result.get("failed"):
                fail_count += 1
                print(f"    {attr_name}: FAILED - {result['failed']}")
        except Exception as e:
            fail_count += 1
            print(f"    {attr_name}: ERROR - {e}")

    print(f"  Done: {success_count} updated, {fail_count} failed")
    return fail_count == 0


def main():
    parser = argparse.ArgumentParser(
        description="Sync Rize time tracking to Exist.io"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="First-time setup: create custom attributes in Exist",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Release old rize_* attributes before setting up new ones",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Sync a specific date (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--no-backfill",
        action="store_true",
        help="Skip syncing yesterday's data",
    )
    args = parser.parse_args()

    config = load_config()
    exist = get_exist_client(config)

    if args.migrate:
        migrate_attributes(exist)
    elif args.setup:
        setup_attributes(exist)
    else:
        if args.date:
            # Specific date requested - just sync that date
            target_date = date.fromisoformat(args.date)
            success = sync_data(config, target_date)
        else:
            # Default: sync today and yesterday (backfill)
            today = date.today()
            yesterday = today - timedelta(days=1)

            success = True
            if not args.no_backfill:
                print("=== Backfilling yesterday ===")
                success = sync_data(config, yesterday) and success
                print()

            print("=== Syncing today ===")
            success = sync_data(config, today) and success

        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
