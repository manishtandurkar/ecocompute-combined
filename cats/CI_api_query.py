"""
CATS Carbon Intensity API Query
"""

from datetime import datetime, timezone

import requests_cache

from .forecast import CarbonIntensityPointEstimate


def get_CI_forecast(
    location: str, CI_API_interface
) -> list[CarbonIntensityPointEstimate]:
    """
    Get carbon intensity forecast from an API.
    
    Args:
        location: Location code (e.g., UK postcode like "M15")
        CI_API_interface: API interface configuration
    
    Returns:
        List of CarbonIntensityPointEstimate objects
    """
    session = requests_cache.CachedSession("cats_cache", use_temp=True)

    r = session.get(
        CI_API_interface.get_request_url(datetime.now(timezone.utc), location)
    )
    data = r.json()

    return CI_API_interface.parse_response_data(data)


if __name__ == "__main__":
    from .CI_api_interface import API_interfaces
    
    # Test with Manchester postcode
    data = get_CI_forecast("M15", API_interfaces["carbonintensity.org.uk"])
    for point in data[:5]:
        print(point)
