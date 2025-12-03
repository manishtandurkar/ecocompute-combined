"""
CATS Forecast Module - Carbon intensity forecasting and windowed analysis.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta


@dataclass(order=True)
class CarbonIntensityPointEstimate:
    """Represents a single data point within an intensity timeseries."""
    value: float  # gCO2/kWh - first attribute for sorting
    datetime: datetime

    def __repr__(self):
        return f"{self.datetime.isoformat()}\t{self.value}"


@dataclass(order=True)
class CarbonIntensityAverageEstimate:
    """Represents a single data point within an integrated carbon intensity timeseries."""
    value: float
    start: datetime
    end: datetime
    start_value: float
    end_value: float


class WindowedForecast:
    """
    Windowed carbon intensity forecast analyzer.
    
    Divides forecast data into overlapping windows of job duration and
    calculates the average carbon intensity for each window.
    """
    
    def __init__(
        self,
        data: list[CarbonIntensityPointEstimate],
        duration: int,  # in minutes
        start: datetime,
        max_window_minutes: Optional[int] = None,
        end_constraint: Optional[datetime] = None,
    ):
        self.duration = duration
        self.max_window_minutes = max_window_minutes
        self.end_constraint = end_constraint

        # Filter data based on constraints
        if max_window_minutes is not None or end_constraint is not None:
            filtered_data = self._filter_data_by_constraints(
                data, start, duration, max_window_minutes or 2820, end_constraint
            )
        else:
            filtered_data = data

        self.data_stepsize = filtered_data[1].datetime - filtered_data[0].datetime
        self.start = start
        self.end = start + timedelta(minutes=duration)

        def bisect_right(data, t):
            for i, d in enumerate(data):
                if d.datetime > t:
                    return i - 1
            return len(data) - 1

        self.data = filtered_data[bisect_right(filtered_data, start):]

        def bisect_left(data, t):
            for i, d in enumerate(data):
                if d.datetime + self.data_stepsize >= t:
                    return i + 1
            raise ValueError("No index found for closest data point past job end time")

        self.ndata = bisect_left(self.data, self.end)

    def _filter_data_by_constraints(
        self,
        data: list[CarbonIntensityPointEstimate],
        start: datetime,
        duration: int,
        max_window_minutes: int,
        end_constraint: Optional[datetime],
    ) -> list[CarbonIntensityPointEstimate]:
        """Filter forecast data based on time constraints."""
        search_window_end = start + timedelta(minutes=max_window_minutes)

        if end_constraint:
            if end_constraint.tzinfo != start.tzinfo:
                end_constraint = end_constraint.astimezone(start.tzinfo)
            search_window_end = min(search_window_end, end_constraint)

        max_data_time = search_window_end + timedelta(minutes=duration)

        filtered_data = []
        for d in data:
            if d.datetime <= max_data_time:
                filtered_data.append(d)
            else:
                break

        if len(filtered_data) < 2:
            raise ValueError(
                "Insufficient forecast data for the specified time window constraints."
            )

        return filtered_data

    def __getitem__(self, index: int) -> CarbonIntensityAverageEstimate:
        """Return the average carbon intensity for window at given index."""
        if index >= len(self):
            raise IndexError("Window index out of range")

        window_start = self.start + index * self.data_stepsize
        window_end = self.end + index * self.data_stepsize

        lbound = self.interp(
            self.data[index],
            self.data[index + 1],
            when=window_start,
        )
        
        if index + self.ndata == len(self.data):
            rbound = self.data[-1]
        else:
            rbound = self.interp(
                self.data[index + self.ndata - 1],
                self.data[index + self.ndata],
                when=window_end,
            )
        
        window_data = [lbound] + self.data[index + 1: index + self.ndata] + [rbound]
        acc = [
            0.5 * (a.value + b.value) * (b.datetime - a.datetime).total_seconds()
            for a, b in zip(window_data[:-1], window_data[1:])
        ]
        duration = window_data[-1].datetime - window_data[0].datetime
        
        return CarbonIntensityAverageEstimate(
            start=window_start,
            end=window_end,
            value=sum(acc) / duration.total_seconds(),
            start_value=lbound.value,
            end_value=rbound.value,
        )

    @staticmethod
    def interp(
        p1: CarbonIntensityPointEstimate,
        p2: CarbonIntensityPointEstimate,
        when: datetime,
    ) -> CarbonIntensityPointEstimate:
        """Linear interpolation between two points."""
        timestep = (p2.datetime - p1.datetime).total_seconds()
        slope = (p2.value - p1.value) / timestep
        offset = (when - p1.datetime).total_seconds()

        return CarbonIntensityPointEstimate(
            value=p1.value + slope * offset,
            datetime=when,
        )

    def __iter__(self):
        for index in range(len(self)):
            yield self[index]

    def __len__(self):
        """Return number of valid forecast windows."""
        base_length = len(self.data) - self.ndata

        if base_length <= 0:
            return 0

        max_valid_index = base_length - 1

        if self.max_window_minutes is not None:
            data_stepsize_minutes = self.data_stepsize.total_seconds() / 60
            max_index_by_window = int(self.max_window_minutes / data_stepsize_minutes)
            max_valid_index = min(max_valid_index, max_index_by_window)

        if self.end_constraint:
            if self.end_constraint.tzinfo != self.start.tzinfo:
                end_constraint = self.end_constraint.astimezone(self.start.tzinfo)
            else:
                end_constraint = self.end_constraint

            for i in range(min(base_length, max_valid_index + 1)):
                window_start = self.start + i * self.data_stepsize
                if window_start >= end_constraint:
                    max_valid_index = i - 1
                    break

        return max(0, max_valid_index + 1)
