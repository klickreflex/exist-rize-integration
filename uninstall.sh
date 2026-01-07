#!/bin/bash
# Uninstall the launchd service

PLIST_NAME="io.exist.rize-sync.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [ -f "$PLIST_DEST" ]; then
    echo "Unloading service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true

    echo "Removing plist..."
    rm "$PLIST_DEST"

    echo "Done!"
else
    echo "Service not installed."
fi
