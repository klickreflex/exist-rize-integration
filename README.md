# Rize to Exist.io Integration

A Python script that syncs time tracking data from [Rize](https://rize.io) to [Exist.io](https://exist.io).

## What it does

- Reads time tracking metrics from Rize's GraphQL API
- Writes them as custom attributes to Exist.io
- Runs automatically on a schedule (6am-9pm, hourly)

### Attributes synced

| Exist Attribute | Source | Type | Description |
|-----------------|--------|------|-------------|
| `focus_time` | `focusTime` | Duration | Time spent in focused work |
| `tracked_time` | `trackedTime` | Duration | Total tracked time |
| `break_time` | `breakTime` | Duration | Time spent on breaks |
| `meeting_time` | `meetingTime` | Duration | Time in meetings |
| `coding_time` | Category "code" | Duration | Time spent coding |
| `design_time` | Category "design" | Duration | Time spent designing |
| `focus_sessions` | Session count | Integer | Number of focus blocks |

## Requirements

- macOS (for launchd scheduling) or Linux (use cron instead)
- Python 3.8+
- A [Rize](https://rize.io) account with API key
- An [Exist.io](https://exist.io) account with OAuth2 app credentials

## Installation

### 1. Clone and set up Python environment

```bash
cd exist-rize-integration
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```
RIZE_API_KEY=your_rize_api_key
EXIST_CLIENT_ID=your_exist_client_id
EXIST_CLIENT_SECRET=your_exist_client_secret
EXIST_ACCESS_TOKEN=your_exist_access_token
EXIST_REFRESH_TOKEN=your_exist_refresh_token
```

**Getting credentials:**

- **Rize API Key**: Rize app → Settings → API
- **Exist OAuth2**: [exist.io/account/apps](https://exist.io/account/apps) → Create new app
  - Set OAuth2 client type to "Confidential"
  - Set Redirect URI to `http://localhost:8080/callback`
  - After creating, generate a developer token for yourself

### 3. Create Exist attributes (first time only)

```bash
source .venv/bin/activate
python3 sync.py --setup
```

This creates the custom attributes in your Exist account and acquires ownership.

### 4. Test the sync

```bash
python3 sync.py
```

You should see output like:
```
Syncing data for 2026-01-07...
  Fetching from Rize...
  Rize data: focus=47min, tracked=67min
  Updating Exist...
    rize_focus_time: {'success': [...], 'failed': []}
    rize_tracked_time: {'success': [...], 'failed': []}
  Sync complete!
```

### 5. Install automatic scheduling (macOS)

```bash
./install.sh
```

This installs a launchd service that runs the sync hourly from 6am-9pm.

## Usage

### Manual sync

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Sync today's data
python3 sync.py

# Sync a specific date
python3 sync.py --date 2026-01-06

# Re-run setup (if attributes were deleted)
python3 sync.py --setup

# Migrate from old attribute names (one-time, if upgrading)
python3 sync.py --migrate
```

### Scheduler management

```bash
# Check if scheduler is running
launchctl list | grep rize

# View sync logs
tail -f sync.log

# Uninstall scheduler
./uninstall.sh

# Reinstall after changing schedule
./install.sh
```

## Project structure

```
exist-rize-integration/
├── .env                    # Your API credentials (gitignored)
├── .env.example            # Template for credentials
├── .gitignore
├── requirements.txt        # Python dependencies
├── rize_client.py          # Rize GraphQL API client
├── exist_client.py         # Exist REST API client
├── sync.py                 # Main sync script
├── io.exist.rize-sync.plist # macOS launchd config
├── install.sh              # Install scheduler
├── uninstall.sh            # Remove scheduler
└── sync.log                # Sync output log (created on first run)
```

## Technical details

### Rize API

- **Endpoint**: `https://api.rize.io/api/v1/graphql`
- **Auth**: Bearer token (API key)
- **Query used**: `summaries` with `bucketSize: "day"`

### Exist API

- **Endpoint**: `https://exist.io/api/2/`
- **Auth**: OAuth2 Bearer token
- **Endpoints used**:
  - `POST /attributes/create/` - Create custom attributes
  - `POST /attributes/acquire/` - Take ownership of attributes
  - `POST /attributes/update/` - Write daily values

### Token refresh

The Exist access token expires after 1 year. The script automatically refreshes it using the refresh token and updates `.env` with the new tokens.

## Troubleshooting

### "command not found: python"

Use `python3` instead of `python`:
```bash
python3 sync.py
```

Or activate the virtual environment first:
```bash
source .venv/bin/activate
python sync.py
```

### "User doesn't have an attribute named 'rize_focus_time'"

Run setup first:
```bash
python3 sync.py --setup
```

### Scheduler not running

Check if it's loaded:
```bash
launchctl list | grep rize
```

If not listed, reinstall:
```bash
./install.sh
```

### No data from Rize

- Ensure Rize desktop app is running and tracking
- Check that your API key is valid
- Rize only returns data for dates with tracked activity

## License

MIT
