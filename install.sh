#!/bin/bash
# Install the launchd service for automatic syncing

set -e

PLIST_NAME="io.exist.rize-sync.plist"
PLIST_SRC="$(dirname "$0")/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

# Check if plist exists
if [ ! -f "$PLIST_SRC" ]; then
    echo "Error: $PLIST_SRC not found"
    exit 1
fi

# Unload if already loaded
if launchctl list | grep -q "io.exist.rize-sync"; then
    echo "Unloading existing service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Copy plist to LaunchAgents
echo "Installing to $PLIST_DEST..."
cp "$PLIST_SRC" "$PLIST_DEST"

# Load the service
echo "Loading service..."
launchctl load "$PLIST_DEST"

echo "Done! The sync will run hourly from 9am-6pm."
echo "To check status: launchctl list | grep rize"
echo "To view logs: tail -f $(dirname "$0")/sync.log"
