"""
GPU Emissions Tracker - Track GPU job emissions using CodeCarbon.
"""

from datetime import datetime
from typing import Dict, List, Optional
import os
import json

import pandas as pd

# CodeCarbon has compatibility issues with Python 3.13
# We catch all exceptions, not just ImportError
_CODECARBON_AVAILABLE = False

class _DummyTracker:
    """Fallback tracker when CodeCarbon is unavailable."""
    def __init__(self, *args, **kwargs):
        self._started = False

    def start(self):
        self._started = True

    def stop(self):
        return 0.0

try:
    from codecarbon import OfflineEmissionsTracker, EmissionsTracker
    _CODECARBON_AVAILABLE = True
except (ImportError, ValueError, Exception) as e:
    # ValueError: Python 3.13 dataclass compatibility issue
    # ImportError: codecarbon not installed
    OfflineEmissionsTracker = _DummyTracker
    EmissionsTracker = _DummyTracker


class GPUEmissionsTracker:
    """Track GPU job emissions using CodeCarbon."""
    
    def __init__(self, country_code: str = "IN", output_dir: str = "data"):
        self.country_code = country_code
        self.output_dir = output_dir
        self.tracker = None
        self.emissions_log: List[Dict] = []
        self.current_job: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.load_emissions_log()
    
    @property
    def is_codecarbon_available(self) -> bool:
        return _CODECARBON_AVAILABLE
    
    def load_emissions_log(self):
        """Load existing emissions data."""
        os.makedirs(self.output_dir, exist_ok=True)
        log_file = os.path.join(self.output_dir, "emissions.json")
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    self.emissions_log = json.load(f)
            except (json.JSONDecodeError, TypeError):
                self.emissions_log = []
    
    def save_emissions_log(self):
        """Save emissions data."""
        os.makedirs(self.output_dir, exist_ok=True)
        log_file = os.path.join(self.output_dir, "emissions.json")
        with open(log_file, 'w') as f:
            json.dump(self.emissions_log, f, indent=2)
    
    def start_tracking(self, job_name: str):
        """Start tracking emissions for a job."""
        try:
            if _CODECARBON_AVAILABLE:
                # Try online mode first (with internet)
                try:
                    self.tracker = EmissionsTracker(
                        project_name=f"ecocompute_{job_name}",
                        log_level="WARNING"
                    )
                except Exception:
                    # Fallback to offline mode
                    self.tracker = OfflineEmissionsTracker(
                        country_iso_code=self.country_code,
                        log_level="WARNING"
                    )
            else:
                self.tracker = _DummyTracker()
            
            self.tracker.start()
            self.current_job = job_name
            self.start_time = datetime.now()
        except Exception as e:
            print(f"Error starting emissions tracker: {e}")
            self.tracker = _DummyTracker()
            self.tracker.start()
            self.current_job = job_name
            self.start_time = datetime.now()
    
    def stop_tracking(self) -> Dict:
        """Stop tracking and return emissions data."""
        if not self.tracker or not self.start_time:
            return {}
        
        try:
            emissions = self.tracker.stop()
            if emissions is None:
                emissions = 0.0
        except Exception:
            emissions = 0.0
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        record = {
            'job_name': self.current_job,
            'emissions_kg_co2': emissions,
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat(),
            'country': self.country_code
        }
        
        self.emissions_log.append(record)
        self.save_emissions_log()
        
        # Reset state
        self.tracker = None
        self.current_job = None
        self.start_time = None
        
        return record
    
    def estimate_emissions(
        self,
        duration_minutes: int,
        power_watts: int,
        carbon_intensity_g_kwh: float
    ) -> float:
        """
        Estimate emissions without actually tracking.
        
        Args:
            duration_minutes: Job duration in minutes
            power_watts: GPU power draw in watts
            carbon_intensity_g_kwh: Grid carbon intensity in gCO2/kWh
        
        Returns:
            Estimated emissions in kg CO2
        """
        power_kw = power_watts / 1000
        duration_h = duration_minutes / 60
        carbon_intensity_kg = carbon_intensity_g_kwh / 1000
        
        return power_kw * duration_h * carbon_intensity_kg
    
    def get_total_emissions(self) -> float:
        """Get cumulative emissions tracked."""
        return sum(job.get('emissions_kg_co2', 0) for job in self.emissions_log)
    
    def get_emissions_summary(self) -> Dict:
        """Get emissions summary statistics."""
        if not self.emissions_log:
            return {
                'total_jobs': 0,
                'total_emissions_kg': 0,
                'avg_emissions_per_job_kg': 0,
                'total_duration_hours': 0,
                'max_single_job_kg': 0,
                'min_single_job_kg': 0
            }
        
        df = pd.DataFrame(self.emissions_log)
        
        return {
            'total_jobs': len(df),
            'total_emissions_kg': df['emissions_kg_co2'].sum(),
            'avg_emissions_per_job_kg': df['emissions_kg_co2'].mean(),
            'total_duration_hours': df['duration_seconds'].sum() / 3600,
            'max_single_job_kg': df['emissions_kg_co2'].max(),
            'min_single_job_kg': df['emissions_kg_co2'].min()
        }
    
    def add_manual_record(
        self,
        job_name: str,
        emissions_kg: float,
        duration_seconds: float,
        avoided_kg: float = 0.0
    ):
        """Add a manual emissions record (for estimated/calculated values)."""
        record = {
            'job_name': job_name,
            'emissions_kg_co2': emissions_kg,
            'emissions_avoided_kg': avoided_kg,
            'duration_seconds': duration_seconds,
            'timestamp': datetime.now().isoformat(),
            'country': self.country_code,
            'is_estimated': True
        }
        
        self.emissions_log.append(record)
        self.save_emissions_log()
        return record


# Export singleton
tracker = GPUEmissionsTracker(country_code="IN")
