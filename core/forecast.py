"""
Forecast Module - Carbon intensity forecasting and optimal time window finding.
Combines CATS WindowedForecast algorithm with mock data generation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
import random


@dataclass(order=True)
class CarbonIntensityPoint:
    """Represents a single carbon intensity data point."""
    value: float  # gCO2/kWh
    datetime: datetime

    def __repr__(self):
        return f"{self.datetime.isoformat()}\t{self.value:.1f} gCO2/kWh"


@dataclass(order=True)
class CarbonIntensityWindow:
    """Represents an average carbon intensity over a time window."""
    value: float  # Average gCO2/kWh
    start: datetime
    end: datetime
    start_value: float  # CI at start time
    end_value: float    # CI at end time


def generate_mock_forecast(region: str = "GB", hours: int = 48) -> List[CarbonIntensityPoint]:
    """
    Generate a mock carbon intensity forecast.
    
    Simulates realistic carbon intensity patterns:
    - Low intensity during night hours (2-6 AM): 80-120 gCO2/kWh
    - Medium intensity during day (7 AM-5 PM): 150-200 gCO2/kWh
    - High intensity during evening peak (6-10 PM): 220-280 gCO2/kWh
    
    Args:
        region: Geographic region (affects base intensity)
        hours: Number of hours to forecast
    
    Returns:
        List of CarbonIntensityPoint objects
    """
    # Base intensity by region
    base_multipliers = {
        "GB": 1.0,
        "IN": 3.5,
        "US": 2.0,
        "DE": 1.8,
        "NO": 0.3,
        "AU": 3.0,
        "FR": 0.4,
    }
    base_mult = base_multipliers.get(region, 1.0)
    
    start_time = datetime.now(timezone.utc)
    # Round to nearest half hour
    if start_time.minute < 30:
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
    else:
        start_time = start_time.replace(minute=30, second=0, microsecond=0)
    
    forecast = []
    num_points = hours * 2  # 30-minute intervals
    
    for i in range(num_points):
        timestamp = start_time + timedelta(minutes=30 * i)
        hour = timestamp.hour
        
        # Simulate realistic patterns
        if 2 <= hour < 6:
            # Night: low carbon intensity (renewable energy dominates)
            base_intensity = 90
            variation = 20
        elif 6 <= hour < 9:
            # Morning: ramping up
            base_intensity = 150
            variation = 30
        elif 9 <= hour < 17:
            # Day: moderate intensity
            base_intensity = 180
            variation = 40
        elif 17 <= hour < 22:
            # Evening peak: high intensity
            base_intensity = 250
            variation = 30
        else:
            # Late evening: decreasing
            base_intensity = 140
            variation = 30
        
        # Apply region multiplier and add variation
        intensity = (base_intensity * base_mult) + (i % 7 - 3) * (variation / 10)
        intensity += random.uniform(-10, 10)  # Small random noise
        
        forecast.append(CarbonIntensityPoint(
            value=max(20, intensity),
            datetime=timestamp
        ))
    
    return forecast


class WindowedForecast:
    """
    Implements the CATS WindowedForecast algorithm.
    
    Divides forecast data into overlapping windows of job duration and
    calculates average carbon intensity for each window.
    """
    
    def __init__(
        self,
        data: List[CarbonIntensityPoint],
        duration: int,  # in minutes
        start: datetime,
        max_window_minutes: Optional[int] = None
    ):
        self.duration = duration
        self.max_window_minutes = max_window_minutes or 2820  # 47 hours default
        
        # Calculate time step from data
        if len(data) >= 2:
            self.data_stepsize = data[1].datetime - data[0].datetime
        else:
            self.data_stepsize = timedelta(minutes=30)
        
        self.start = start
        self.end = start + timedelta(minutes=duration)
        
        # Filter data to start from the job start time
        filtered_data = [d for d in data if d.datetime >= start - self.data_stepsize]
        self.data = filtered_data if filtered_data else data
        
        # Calculate window size (number of data points)
        self.ndata = max(1, int(duration / (self.data_stepsize.total_seconds() / 60)) + 1)
    
    def __getitem__(self, index: int) -> CarbonIntensityWindow:
        """Return average carbon intensity for window at given index."""
        if index >= len(self):
            raise IndexError("Window index out of range")
        
        window_start = self.start + index * self.data_stepsize
        window_end = window_start + timedelta(minutes=self.duration)
        
        # Get data points within window
        window_data = []
        for d in self.data:
            if window_start <= d.datetime <= window_end:
                window_data.append(d)
        
        if not window_data:
            # Fallback: use nearest data points
            window_data = self.data[index:index + self.ndata]
        
        if not window_data:
            return CarbonIntensityWindow(
                value=0,
                start=window_start,
                end=window_end,
                start_value=0,
                end_value=0
            )
        
        # Calculate average using trapezoidal rule
        total = sum(d.value for d in window_data)
        avg_value = total / len(window_data)
        
        return CarbonIntensityWindow(
            value=avg_value,
            start=window_start,
            end=window_end,
            start_value=window_data[0].value,
            end_value=window_data[-1].value
        )
    
    def __iter__(self):
        for index in range(len(self)):
            yield self[index]
    
    def __len__(self):
        """Return number of valid forecast windows."""
        max_windows = len(self.data) - self.ndata + 1
        
        if self.max_window_minutes:
            stepsize_minutes = self.data_stepsize.total_seconds() / 60
            max_by_window = int(self.max_window_minutes / stepsize_minutes)
            max_windows = min(max_windows, max_by_window)
        
        return max(1, max_windows)


def get_best_start_time(
    duration_minutes: int,
    region: str = "GB",
    max_window_hours: int = 24
) -> Tuple[datetime, float]:
    """
    Find the optimal start time for a job to minimize carbon emissions.
    
    Args:
        duration_minutes: Expected duration of the job in minutes
        region: Geographic region
        max_window_hours: Maximum hours to look ahead (default: 24)
    
    Returns:
        Tuple of (optimal_start_time, average_carbon_intensity)
    
    Example:
        >>> start_time, ci = get_best_start_time(60, region="GB")
        >>> print(f"Best start time: {start_time}, CI: {ci:.2f} gCO2/kWh")
    """
    if duration_minutes < 1:
        raise ValueError("Duration must be at least 1 minute")
    
    max_window_minutes = max_window_hours * 60
    if duration_minutes > max_window_minutes:
        raise ValueError(
            f"Job duration ({duration_minutes} min) exceeds window ({max_window_minutes} min)"
        )
    
    # Generate forecast
    forecast = generate_mock_forecast(region=region, hours=max_window_hours + 2)
    
    # Get current time
    current_time = datetime.now(timezone.utc)
    
    # Create windowed forecast
    windowed = WindowedForecast(
        data=forecast,
        duration=duration_minutes,
        start=current_time,
        max_window_minutes=max_window_minutes
    )
    
    # Find minimum carbon intensity window
    best_window = min(windowed)
    
    return best_window.start, best_window.value


def get_current_vs_optimal(
    duration_minutes: int,
    region: str = "GB",
    max_window_hours: int = 24
) -> Tuple[CarbonIntensityWindow, CarbonIntensityWindow]:
    """
    Compare running now vs optimal time.
    
    Returns:
        Tuple of (now_window, optimal_window)
    """
    forecast = generate_mock_forecast(region=region, hours=max_window_hours + 2)
    current_time = datetime.now(timezone.utc)
    
    windowed = WindowedForecast(
        data=forecast,
        duration=duration_minutes,
        start=current_time,
        max_window_minutes=max_window_hours * 60
    )
    
    now_window = windowed[0]
    optimal_window = min(windowed)
    
    return now_window, optimal_window
