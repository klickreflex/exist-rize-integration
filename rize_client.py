"""
Rize GraphQL API client for fetching time tracking data.
"""
import requests
from datetime import date, datetime


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


def get_daily_summary(api_key: str, target_date: date) -> dict:
    """
    Fetch all time metrics for a specific date from Rize.

    Args:
        api_key: Rize API key
        target_date: The date to fetch data for

    Returns:
        dict with all time metrics in seconds
    """
    date_str = target_date.isoformat()

    query = """
    query DailySummary($startDate: ISO8601Date!, $endDate: ISO8601Date!) {
        summaries(startDate: $startDate, endDate: $endDate, bucketSize: "day") {
            focusTime
            trackedTime
            breakTime
            meetingTime
        }
    }
    """

    data = _make_request(api_key, query, {
        "startDate": date_str,
        "endDate": date_str,
    })

    summaries = data["summaries"]

    return {
        "focus_time": summaries["focusTime"],
        "tracked_time": summaries["trackedTime"],
        "break_time": summaries["breakTime"],
        "meeting_time": summaries["meetingTime"],
    }


def get_category_times(api_key: str, target_date: date) -> dict:
    """
    Fetch time spent per category for a specific date.

    Args:
        api_key: Rize API key
        target_date: The date to fetch data for

    Returns:
        dict mapping category keys to time in seconds
    """
    start = datetime.combine(target_date, datetime.min.time()).isoformat() + "Z"
    end = datetime.combine(target_date, datetime.max.time()).isoformat() + "Z"

    query = """
    query CategoryTimes($startTime: ISO8601DateTime!, $endTime: ISO8601DateTime!) {
        categories(startTime: $startTime, endTime: $endTime) {
            category {
                key
                name
            }
            timeSpent
        }
    }
    """

    data = _make_request(api_key, query, {
        "startTime": start,
        "endTime": end,
    })

    return {
        cat["category"]["key"]: cat["timeSpent"]
        for cat in data["categories"]
    }


def get_session_counts(api_key: str, target_date: date) -> dict:
    """
    Count sessions by type for a specific date.

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
        }
    }
    """

    data = _make_request(api_key, query, {
        "startTime": start,
        "endTime": end,
    })

    counts = {"focus": 0, "break": 0, "meeting": 0}
    for session in data["sessions"]:
        session_type = session["type"]
        if session_type in counts:
            counts[session_type] += 1

    return {
        "focus_sessions": counts["focus"],
        "break_sessions": counts["break"],
        "meeting_sessions": counts["meeting"],
    }


def get_all_daily_data(api_key: str, target_date: date) -> dict:
    """
    Fetch all available metrics for a specific date.

    Args:
        api_key: Rize API key
        target_date: The date to fetch data for

    Returns:
        dict with all metrics
    """
    summary = get_daily_summary(api_key, target_date)
    categories = get_category_times(api_key, target_date)
    sessions = get_session_counts(api_key, target_date)

    return {
        # From summary (in seconds)
        "focus_time": summary["focus_time"],
        "tracked_time": summary["tracked_time"],
        "break_time": summary["break_time"],
        "meeting_time": summary["meeting_time"],
        # From categories (in seconds)
        "coding_time": categories.get("code", 0),
        "design_time": categories.get("design", 0),
        # From sessions (counts)
        "focus_sessions": sessions["focus_sessions"],
    }
