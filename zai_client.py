"""
zai_client.py — Reusable Z.ai quota API client
Usage in other projects:
    from zai_client import ZaiClient
    client = ZaiClient(bearer_token="your_token")
    data = client.get_quota()
"""

import requests
from dataclasses import dataclass, field
from typing import Optional
import time


QUOTA_URL = "https://api.z.ai/api/monitor/usage/quota/limit"


@dataclass
class UsageDetail:
    model_code: str
    usage: int


@dataclass
class LimitInfo:
    type: str          # TIME_LIMIT or TOKENS_LIMIT
    unit: int
    number: int
    usage: Optional[int] = None
    current_value: Optional[int] = None
    remaining: Optional[int] = None
    percentage: int = 0
    next_reset_time: Optional[int] = None
    usage_details: list = field(default_factory=list)

    def next_reset_datetime(self, utc_offset: int = 0) -> str:
        """Return formatted reset time string with UTC offset applied."""
        if self.next_reset_time:
            ts = self.next_reset_time / 1000 + utc_offset * 3600
            return time.strftime('%H:%M %d.%m.%Y', time.gmtime(ts))
        return "—"

    @property
    def label(self):
        # TIME_LIMIT = rolling 5-hour request quota
        # TOKENS_LIMIT = monthly web search/reader/zread quota
        if self.type == "TIME_LIMIT":
            return "Aylık Tool Kota"
        return "5 Saatlik Kota"


@dataclass
class QuotaData:
    level: str
    limits: list
    fetched_at: float = field(default_factory=time.time)
    error: Optional[str] = None

    @property
    def time_limit(self) -> Optional[LimitInfo]:
        for l in self.limits:
            if l.type == "TIME_LIMIT":
                return l
        return None

    @property
    def token_limit(self) -> Optional[LimitInfo]:
        for l in self.limits:
            if l.type == "TOKENS_LIMIT":
                return l
        return None


class ZaiClient:
    """
    Reusable Z.ai API client.
    
    Example:
        client = ZaiClient("Bearer eyJ...")
        quota = client.get_quota()
        print(quota.time_limit.remaining)
    """

    def __init__(self, bearer_token: str, timeout: int = 10):
        # Accept both "Bearer xxx" and raw token
        if not bearer_token.startswith("Bearer "):
            bearer_token = f"Bearer {bearer_token}"
        self.bearer_token = bearer_token
        self.timeout = timeout
        self._headers = {
            "Authorization": self.bearer_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_quota(self) -> QuotaData:
        """Fetch quota/limit data from Z.ai. Returns QuotaData with error field on failure."""
        try:
            resp = requests.get(QUOTA_URL, headers=self._headers, timeout=self.timeout)
            resp.raise_for_status()
            body = resp.json()

            if not body.get("success"):
                return QuotaData(level="—", limits=[], error=body.get("msg", "API error"))

            raw = body["data"]
            limits = []
            for l in raw.get("limits", []):
                details = [
                    UsageDetail(d["modelCode"], d["usage"])
                    for d in l.get("usageDetails", [])
                ]
                limits.append(LimitInfo(
                    type=l.get("type", ""),
                    unit=l.get("unit", 0),
                    number=l.get("number", 0),
                    usage=l.get("usage"),
                    current_value=l.get("currentValue"),
                    remaining=l.get("remaining"),
                    percentage=l.get("percentage", 0),
                    next_reset_time=l.get("nextResetTime"),
                    usage_details=details,
                ))
            return QuotaData(level=raw.get("level", "—"), limits=limits)

        except requests.exceptions.ConnectionError:
            return QuotaData(level="—", limits=[], error="Connection failed")
        except requests.exceptions.Timeout:
            return QuotaData(level="—", limits=[], error="Request timed out")
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else "?"
            if code == 401:
                return QuotaData(level="—", limits=[], error="Invalid token (401)")
            return QuotaData(level="—", limits=[], error=f"HTTP {code}")
        except Exception as e:
            return QuotaData(level="—", limits=[], error=str(e))