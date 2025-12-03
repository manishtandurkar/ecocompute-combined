"""
CATS Carbon Footprint Calculator
"""

import datetime
from collections import namedtuple

Estimates = namedtuple("Estimates", ["now", "best", "savings"])


def get_footprint_reduction_estimate(
    PUE: float,
    jobinfo: list[tuple[int, float]],
    runtime: datetime.timedelta,
    average_best_ci: float,  # in gCO2/kWh
    average_now_ci: float,
) -> Estimates:
    """
    Calculate carbon footprint estimates for a job.
    
    Args:
        PUE: Power Usage Effectiveness (typically 1.1-2.0)
        jobinfo: List of (num_units, power_watts) tuples
        runtime: Job runtime as timedelta
        average_best_ci: Average carbon intensity at optimal time (gCO2/kWh)
        average_now_ci: Average carbon intensity now (gCO2/kWh)
    
    Returns:
        Estimates namedtuple with (now, best, savings) in gCO2
    """
    # Calculate energy in kWh
    energy = (
        PUE
        * (runtime.total_seconds() / 3600)
        * sum([(nunits * power) for nunits, power in jobinfo])
        / 1000
    )
    
    best = energy * average_best_ci
    now = energy * average_now_ci

    return Estimates(now, best, now - best)
