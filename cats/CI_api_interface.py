"""
CATS Carbon Intensity API Interface
"""

import sys
from collections import namedtuple
from datetime import datetime
from zoneinfo import ZoneInfo

from .forecast import CarbonIntensityPointEstimate


class InvalidLocationError(Exception):
    pass


APIInterface = namedtuple(
    "APIInterface", ["get_request_url", "parse_response_data", "max_duration"]
)


def ciuk_request_url(timestamp: datetime, postcode: str):
    """Generate URL for UK Carbon Intensity API."""
    if timestamp.minute > 30:
        dt = timestamp.replace(minute=31, second=0, microsecond=0)
    else:
        dt = timestamp.replace(minute=1, second=0, microsecond=0)

    if len(postcode) > 4:
        sys.stderr.write(f"Warning: truncating postcode {postcode} to ")
        postcode = postcode[:-3].strip()
        sys.stderr.write(f"{postcode}.\n")

    return (
        "https://api.carbonintensity.org.uk/regional/intensity/"
        + dt.strftime("%Y-%m-%dT%H:%MZ")
        + "/fw48h/postcode/"
        + postcode
    )


def ciuk_parse_response_data(response: dict):
    """Parse response from UK Carbon Intensity API."""
    def invalid_code(r: dict) -> bool:
        try:
            return "postcode" in r["error"]["message"]
        except KeyError:
            return False

    if (not response) or invalid_code(response):
        raise InvalidLocationError

    datefmt = "%Y-%m-%dT%H:%MZ"
    utc = ZoneInfo("UTC")
    
    return [
        CarbonIntensityPointEstimate(
            datetime=datetime.strptime(d["from"], datefmt).replace(tzinfo=utc),
            value=d["intensity"]["forecast"],
        )
        for d in response["data"]["data"]
    ]


API_interfaces = {
    "carbonintensity.org.uk": APIInterface(
        get_request_url=ciuk_request_url,
        parse_response_data=ciuk_parse_response_data,
        max_duration=2820,  # 47 hours
    ),
}
