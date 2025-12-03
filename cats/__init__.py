"""
CATS - Climate Aware Task Scheduler
Python library for carbon-aware job scheduling.
"""

from .forecast import (
    CarbonIntensityPointEstimate,
    CarbonIntensityAverageEstimate,
    WindowedForecast,
)
from .CI_api_interface import API_interfaces, InvalidLocationError
from .CI_api_query import get_CI_forecast
from .carbonFootprint import Estimates, get_footprint_reduction_estimate

__version__ = "1.1.0"

__all__ = [
    'CarbonIntensityPointEstimate',
    'CarbonIntensityAverageEstimate',
    'WindowedForecast',
    'API_interfaces',
    'InvalidLocationError',
    'get_CI_forecast',
    'Estimates',
    'get_footprint_reduction_estimate',
]
