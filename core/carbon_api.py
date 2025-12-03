"""
Carbon Data Provider - Multi-source carbon intensity API
Combines real API calls with mock data fallback for demos.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import random

import requests


class CarbonDataProvider:
    """Fetches real-time grid carbon intensity from multiple sources."""
    
    def __init__(self):
        self.electricity_maps_token = os.getenv("ELECTRICITY_MAPS_TOKEN", "demo")
        self.cache = {}
        self.cache_duration = timedelta(minutes=5)
    
    def get_grid_carbon_intensity(self, region: str = "IN") -> Dict:
        """
        Fetch carbon intensity for a region.
        
        Args:
            region: ISO code (IN=India, US=USA, DE=Germany, NO=Norway, AU=Australia, GB=UK)
        
        Returns:
            {
                'carbonIntensity': float (gCO2/kWh),
                'timestamp': str,
                'greenness': 'LOW'|'MEDIUM'|'HIGH',
                'recommendation': str
            }
        """
        # Check cache first
        cache_key = f"{region}_{datetime.now().strftime('%Y%m%d%H%M')}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Try ElectricityMaps API (free tier)
            if self.electricity_maps_token != "demo":
                url = "https://api.electricitymap.com/v3/carbon-intensity/latest"
                params = {
                    "countryCode": region,
                    "auth-token": self.electricity_maps_token
                }
                
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    carbon_intensity = data.get("carbonIntensity", 500)
                    result = self._format_response(carbon_intensity, region, is_mock=False)
                    self.cache[cache_key] = result
                    return result
            
            # Fallback to mock data
            return self._get_mock_data(region)
        
        except Exception as e:
            print(f"Error fetching carbon data: {e}")
            return self._get_mock_data(region)
    
    def _format_response(self, carbon_intensity: float, region: str, is_mock: bool = False) -> Dict:
        """Format the carbon intensity response."""
        if carbon_intensity < 200:
            greenness = "HIGH"
            recommendation = "✅ Schedule jobs NOW - Clean grid"
        elif carbon_intensity < 400:
            greenness = "MEDIUM"
            recommendation = "⏳ Wait for better conditions"
        else:
            greenness = "LOW"
            recommendation = "❌ Defer jobs - Dirty grid"
        
        return {
            'carbonIntensity': carbon_intensity,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'greenness': greenness,
            'recommendation': recommendation,
            'region': region,
            'unit': 'gCO2/kWh',
            'is_mock': is_mock
        }
    
    def _get_mock_data(self, region: str) -> Dict:
        """Return mock data for hackathon demo with realistic patterns."""
        # Base intensities for different regions
        base_intensities = {
            "IN": 700,    # India avg (coal heavy)
            "US": 400,    # USA avg (mixed)
            "DE": 350,    # Germany (transitioning)
            "NO": 50,     # Norway (hydro dominant)
            "AU": 600,    # Australia (coal + solar)
            "GB": 200,    # UK (wind + gas)
            "FR": 80,     # France (nuclear)
        }
        
        base = base_intensities.get(region, 500)
        
        # Add time-of-day variation
        hour = datetime.now().hour
        if 2 <= hour < 6:
            # Night: lower intensity (more renewables in mix)
            variation = -50
        elif 17 <= hour < 22:
            # Evening peak: higher intensity
            variation = 80
        else:
            # Day: moderate
            variation = 20
        
        # Add some randomness
        intensity = max(20, base + variation + random.randint(-50, 50))
        
        return self._format_response(intensity, region, is_mock=True)
    
    def get_multi_region_comparison(self, regions: Optional[List[str]] = None) -> Dict:
        """Compare carbon intensity across multiple regions."""
        if regions is None:
            regions = ["IN", "US", "DE", "NO", "AU", "GB"]
        
        comparison = {}
        for region in regions:
            comparison[region] = self.get_grid_carbon_intensity(region)
        
        # Find greenest region
        greenest_region_code, greenest_data = min(
            comparison.items(),
            key=lambda item: item[1]['carbonIntensity']
        )
        
        return {
            'regions': comparison,
            'greenest_region': greenest_region_code,
            'greenest_intensity': greenest_data['carbonIntensity'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_24h_forecast(self, region: str = "GB") -> List[Dict]:
        """
        Get 24-hour carbon intensity forecast.
        Uses mock data with realistic daily patterns.
        """
        forecast = []
        start_time = datetime.now(timezone.utc)
        
        # Round to nearest half hour
        if start_time.minute < 30:
            start_time = start_time.replace(minute=0, second=0, microsecond=0)
        else:
            start_time = start_time.replace(minute=30, second=0, microsecond=0)
        
        base_intensities = {
            "IN": 700, "US": 400, "DE": 350, "NO": 50,
            "AU": 600, "GB": 200, "FR": 80
        }
        base = base_intensities.get(region, 500)
        
        # Generate 48 data points (24 hours in 30-minute intervals)
        for i in range(48):
            timestamp = start_time + timedelta(minutes=30 * i)
            hour = timestamp.hour
            
            # Simulate realistic patterns
            if 2 <= hour < 6:
                # Night: low intensity (renewables)
                intensity = base * 0.4 + random.randint(-20, 20)
            elif 6 <= hour < 9:
                # Morning ramp
                intensity = base * 0.7 + random.randint(-30, 30)
            elif 9 <= hour < 17:
                # Day: moderate (solar helps)
                intensity = base * 0.8 + random.randint(-40, 40)
            elif 17 <= hour < 22:
                # Evening peak
                intensity = base * 1.1 + random.randint(-30, 30)
            else:
                # Late evening
                intensity = base * 0.6 + random.randint(-25, 25)
            
            forecast.append({
                'datetime': timestamp,
                'value': max(20, intensity),
                'region': region
            })
        
        return forecast


# Export singleton
carbon_provider = CarbonDataProvider()
