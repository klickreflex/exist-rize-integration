"""
Rize GraphQL API client for fetching time tracking data.
"""
import requests
from datetime import date, datetime, timezone


RIZE_API_URL = "https://api.rize.io/api/v1/graphql"


def _make_request(api_key: str, query: str, variables: dict) -> dict:
    """Make a GraphQL request to the Rize API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {"query": query, "variables": variables}
    response = requests.post(RIZE_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    data = response.json()
    if "errors" in data:
        raise RuntimeError(f"Rize API error: {data['errors']}")

    return data["data"]


def get_category_breakdown(api_key: str, target_date: date) -> dict:
    """
    Fetch time spent per category with focus flags for a specific date.

    Args:
        api_key: Rize API key
        target_date: The date to fetch data for

    Returns:
        dict with category times and computed totals
    """
    start = datetime.combine(target_date, datetime.min.time()).isoformat() + "Z"
    end = datetime.combine(target_date, datetime.max.time()).isoformat() + "Z"

    query = """
    query CategoryTimes($startTime: ISO8601DateTime!, $endTime: ISO8601DateTime!) {
        categories(startTime: $startTime, endTime: $endTime) {
            category {
                key
                name
                focus
            }
            timeSpent
        }
    }
    """

    data = _make_request(api_key, query, {
        "startTime": start,
        "endTime": end,
    })

    categories = {}
    total_time = 0
    focus_time = 0

    for cat in data["categories"]:
        key = cat["category"]["key"]
        time_spent = cat["timeSpent"]
        is_focus = cat["category"]["focus"]

        categories[key] = time_spent
        total_time += time_spent
        if is_focus:
            focus_time += time_spent

    return {
        "categories": categories,
        "total_time": total_time,
        "focus_time": focus_time,
    }


def get_session_counts(api_key: str, target_date: date) -> dict:
    """
    Count completed/started sessions by type for a specific date.

    Only counts sessions that have actually started (startTime <= now).

    Args:
        api_key: Rize API key
        target_date: The date to fetch data for

    Returns:
        dict with counts: focus_sessions, break_sessions, meeting_sessions
    """
    start = datetime.combine(target_date, datetime.min.time()).isoformat() + "Z"
    end = datetime.combine(target_date, datetime.max.time()).isoformat() + "Z"

    query = """
    query Sessions($startTime: ISO8601DateTime!, $endTime: ISO8601DateTime!) {
        sessions(startTime: $startTime, endTime: $endTime) {
            type
            startTime
        }
    }
    """

    data = _make_request(api_key, query, {
        "startTime": start,
        "endTime": end,
    })

    now = datetime.now(timezone.utc)
    counts = {"focus": 0, "break": 0, "meeting": 0}

    for session in data["sessions"]:
        # Parse session start time and check if it's in the past
        start_str = session["startTime"]
        # Handle both formats: with and without timezone
        try:
            if "+" in start_str or start_str.endswith("Z"):
                session_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            else:
                # Assume UTC if no timezone
                session_start = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        # Only count sessions that have started
        if session_start <= now:
            session_type = session["type"]
            if session_type in counts:
                counts[session_type] += 1

    return {
        "focus_sessions": counts["focus"],
        "break_sessions": counts["break"],
        "meeting_sessions": counts["meeting"],
    }


def get_meeting_time(api_key: str, target_date: date) -> int:
    """
    Get actual meeting time from completed meeting sessions.

    Args:
        api_key: Rize API key
        target_date: The date to fetch data for

    Returns:
        Meeting time in seconds
    """
    start = datetime.combine(target_date, datetime.min.time()).isoformat() + "Z"
    end = datetime.combine(target_date, datetime.max.time()).isoformat() + "Z"

    query = """
    query Sessions($startTime: ISO8601DateTime!, $endTime: ISO8601DateTime!) {
        sessions(startTime: $startTime, endTime: $endTime) {
            type
            startTime
            endTime
        }
    }
    """

    data = _make_request(api_key, query, {
        "startTime": start,
        "endTime": end,
    })

    now = datetime.now(timezone.utc)
    meeting_seconds = 0

    for session in data["sessions"]:
        if session["type"] != "meeting":
            continue

        try:
            start_str = session["startTime"]
            end_str = session["endTime"]

            if "+" in start_str or start_str.endswith("Z"):
                session_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            else:
                session_start = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)

            if "+" in end_str or end_str.endswith("Z"):
                session_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            else:
                session_end = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)

            # Only count if session has started
            if session_start <= now:
                # Cap end time at now if meeting is ongoing
                effective_end = min(session_end, now)
                duration = (effective_end - session_start).total_seconds()
                if duration > 0:
                    meeting_seconds += int(duration)
        except (ValueError, KeyError):
            continue

    return meeting_seconds


def get_all_daily_data(api_key: str, target_date: date) -> dict:
    """
    Fetch all available metrics for a specific date.

    Uses category breakdown for accurate tracked/focus time,
    and filters sessions to only count completed ones.

    Args:
        api_key: Rize API key
        target_date: The date to fetch data for

    Returns:
        dict with all metrics
    """
    category_data = get_category_breakdown(api_key, target_date)
    sessions = get_session_counts(api_key, target_date)
    meeting_time = get_meeting_time(api_key, target_date)

    categories = category_data["categories"]

    return {
        # Computed from categories (actual tracked activity, in seconds)
        "focus_time": category_data["focus_time"],
        "tracked_time": category_data["total_time"],
        # Specific categories (in seconds)
        "coding_time": categories.get("code", 0),
        "design_time": categories.get("design", 0),
        # From sessions (actual meeting time)
        "meeting_time": meeting_time,
        # Break time = tracked time - focus time (time in non-focus categories)
        "break_time": category_data["total_time"] - category_data["focus_time"],
        # Session counts (only started sessions)
        "focus_sessions": sessions["focus_sessions"],
    }
