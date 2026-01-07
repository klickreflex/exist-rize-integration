#!/usr/bin/env python3
"""
Sync Rize time tracking data to Exist.io custom attributes.

This script fetches focus time and tracked time from Rize and writes
them to Exist.io as custom duration attributes.

Usage:
    python sync.py           # Sync today's data
    python sync.py --setup   # First-time setup (create attributes)
"""
import argparse
import os
import sys
from datetime import date

from dotenv import load_dotenv

from rize_client import get_daily_summary
from exist_client import ExistClient


# Attribute configuration
ATTRIBUTES = {
    "rize_focus_time": {
        "label": "Rize Focus Time",
        "value_type": "duration",
        "group": "productivity",
    },
    "rize_tracked_time": {
        "label": "Rize Tracked Time",
        "value_type": "duration",
        "group": "productivity",
    },
}


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

        # Try to create the attribute (will fail if it already exists)
        try:
            result = exist.create_attribute(
                label=attr_config["label"],
                value_type=attr_config["value_type"],
                group=attr_config["group"],
            )
            print(f"  Created: {attr_name}")

            # Check for success/failure in response
            if isinstance(result, dict):
                if result.get("success"):
                    print(f"    -> {result['success']}")
                if result.get("failed"):
                    print(f"    -> Failed: {result['failed']}")

        except Exception as e:
            # Attribute might already exist, try to acquire it
            print(f"  Could not create {attr_name}: {e}")
            print(f"  Attempting to acquire existing attribute...")

        # Try to acquire ownership
        try:
            exist.acquire_attribute(attr_name)
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
        rize_data = get_daily_summary(config["RIZE_API_KEY"], target_date)
    except Exception as e:
        print(f"  Error fetching Rize data: {e}")
        return False

    focus_seconds = rize_data["focus_time"]
    tracked_seconds = rize_data["tracked_time"]

    # Convert seconds to minutes (Exist duration type uses minutes)
    focus_minutes = focus_seconds // 60
    tracked_minutes = tracked_seconds // 60

    print(f"  Rize data: focus={focus_minutes}min, tracked={tracked_minutes}min")

    # Update Exist
    exist = ExistClient(
        access_token=config["EXIST_ACCESS_TOKEN"],
        refresh_token=config.get("EXIST_REFRESH_TOKEN"),
        client_id=config.get("EXIST_CLIENT_ID"),
        client_secret=config.get("EXIST_CLIENT_SECRET"),
    )

    print("  Updating Exist...")
    try:
        result = exist.update_attribute("rize_focus_time", target_date, focus_minutes)
        print(f"    rize_focus_time: {result}")

        result = exist.update_attribute("rize_tracked_time", target_date, tracked_minutes)
        print(f"    rize_tracked_time: {result}")

    except Exception as e:
        print(f"  Error updating Exist: {e}")
        return False

    print("  Sync complete!")
    return True


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
        "--date",
        type=str,
        help="Sync a specific date (YYYY-MM-DD format)",
    )
    args = parser.parse_args()

    config = load_config()

    exist = ExistClient(
        access_token=config["EXIST_ACCESS_TOKEN"],
        refresh_token=config.get("EXIST_REFRESH_TOKEN"),
        client_id=config.get("EXIST_CLIENT_ID"),
        client_secret=config.get("EXIST_CLIENT_SECRET"),
    )

    if args.setup:
        setup_attributes(exist)
    else:
        target_date = None
        if args.date:
            target_date = date.fromisoformat(args.date)

        success = sync_data(config, target_date)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
