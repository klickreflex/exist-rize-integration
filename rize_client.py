"""
Rize GraphQL API client for fetching time tracking data.
"""
import requests
from datetime import date


RIZE_API_URL = "https://api.rize.io/api/v1/graphql"


def get_daily_summary(api_key: str, target_date: date) -> dict:
    """
    Fetch focus time and tracked time for a specific date from Rize.

    Args:
        api_key: Rize API key
        target_date: The date to fetch data for

    Returns:
        dict with 'focus_time' and 'tracked_time' in seconds
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    date_str = target_date.isoformat()

    query = """
    query DailySummary($startDate: ISO8601Date!, $endDate: ISO8601Date!) {
        summaries(startDate: $startDate, endDate: $endDate, bucketSize: "day") {
            focusTime
            trackedTime
        }
    }
    """

    payload = {
        "query": query,
        "variables": {
            "startDate": date_str,
            "endDate": date_str,
        },
    }

    response = requests.post(RIZE_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(f"Rize API error: {data['errors']}")

    summaries = data["data"]["summaries"]

    return {
        "focus_time": summaries["focusTime"],
        "tracked_time": summaries["trackedTime"],
    }
