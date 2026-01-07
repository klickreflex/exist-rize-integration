"""
Exist.io REST API client for writing custom attributes.
"""
import os
import requests
from datetime import date


EXIST_API_URL = "https://exist.io/api/2"

# Value type codes for Exist API
VALUE_TYPES = {
    "integer": 0,
    "float": 1,
    "string": 2,
    "duration": 3,  # Period in minutes
    "period": 3,
    "percentage": 4,
    "boolean": 5,
    "scale": 6,
    "time": 7,
}


class ExistClient:
    """Client for interacting with the Exist.io API."""

    def __init__(self, access_token: str, refresh_token: str = None,
                 client_id: str = None, client_secret: str = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request, handling token refresh if needed."""
        url = f"{EXIST_API_URL}/{endpoint}"
        response = requests.request(method, url, headers=self._headers(), **kwargs)

        # If unauthorized and we have refresh credentials, try refresh
        if response.status_code == 401 and self.refresh_token:
            if self._refresh_access_token():
                response = requests.request(method, url, headers=self._headers(), **kwargs)

        response.raise_for_status()
        return response.json() if response.text else {}

    def _refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        if not all([self.refresh_token, self.client_id, self.client_secret]):
            return False

        response = requests.post(
            "https://exist.io/oauth2/access_token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data.get("refresh_token", self.refresh_token)
            self._save_new_tokens()
            print("Access token refreshed successfully")
            return True

        print(f"Failed to refresh token: {response.text}")
        return False

    def _save_new_tokens(self):
        """Update the .env file with new tokens."""
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if not os.path.exists(env_path):
            return

        with open(env_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.startswith("EXIST_ACCESS_TOKEN="):
                new_lines.append(f"EXIST_ACCESS_TOKEN={self.access_token}\n")
            elif line.startswith("EXIST_REFRESH_TOKEN="):
                new_lines.append(f"EXIST_REFRESH_TOKEN={self.refresh_token}\n")
            else:
                new_lines.append(line)

        with open(env_path, "w") as f:
            f.writelines(new_lines)

    def get_owned_attributes(self) -> list:
        """Get list of attributes owned by this client."""
        return self._request("GET", "attributes/owned/")

    def create_attribute(self, label: str, value_type: str = "duration",
                         group: str = "custom") -> dict:
        """
        Create a new custom attribute.

        Args:
            label: Human-readable name (e.g., "Rize Focus Time")
            value_type: One of: integer, float, duration, percentage, boolean, scale, time
            group: Attribute group (custom, productivity, etc.)

        Returns:
            The created attribute data including the generated 'name' (slug)
        """
        # Convert string value_type to integer code
        vtype_code = VALUE_TYPES.get(value_type.lower(), 3)  # default to duration

        payload = [{
            "label": label,
            "value_type": vtype_code,
            "group": group,
            "manual": False,
        }]
        result = self._request("POST", "attributes/create/", json=payload)
        return result

    def acquire_attribute(self, attribute_name: str) -> dict:
        """
        Acquire ownership of an existing attribute.

        Args:
            attribute_name: The attribute slug (e.g., "rize_focus_time")
        """
        payload = [{"name": attribute_name, "active": True}]
        return self._request("POST", "attributes/acquire/", json=payload)

    def release_attribute(self, attribute_name: str) -> dict:
        """Release ownership of an attribute."""
        payload = [{"name": attribute_name}]
        return self._request("POST", "attributes/release/", json=payload)

    def update_attribute(self, attribute_name: str, target_date: date, value: int) -> dict:
        """
        Update an attribute value for a specific date.

        Args:
            attribute_name: The attribute slug
            target_date: The date to update
            value: The value (for duration type, this is in minutes)
        """
        payload = [{
            "name": attribute_name,
            "date": target_date.isoformat(),
            "value": value,
        }]
        return self._request("POST", "attributes/update/", json=payload)

    def get_user_attributes(self) -> list:
        """Get all attributes for the current user."""
        return self._request("GET", "attributes/")
