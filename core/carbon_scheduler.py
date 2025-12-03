"""
Carbon-Aware Scheduler - Main scheduling logic combining job queue and carbon API.
"""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import time

from .job_queue import JobQueue, GPUJob, JobStatus
from .carbon_api import CarbonDataProvider, carbon_provider
from .emissions_tracker import GPUEmissionsTracker, tracker
from .forecast import (
    get_best_start_time,
    get_current_vs_optimal,
    generate_mock_forecast,
    WindowedForecast
)


class CarbonAwareScheduler:
    """Main scheduler that decides when to run GPU jobs based on carbon intensity."""
    
    def __init__(self):
        self.job_queue = JobQueue()
        self.carbon_provider = carbon_provider
        self.emissions_tracker = tracker
        self.schedule_history: List[Dict] = []
    
    def schedule_pending_jobs(self, region: str = "IN") -> Dict:
        """
        Evaluate pending jobs and schedule/defer based on grid carbon intensity.
        
        Args:
            region: Grid region code
        
        Returns:
            Summary of scheduled and deferred jobs
        """
        # Get current grid status
        grid_status = self.carbon_provider.get_grid_carbon_intensity(region)
        carbon_intensity = grid_status['carbonIntensity']
        greenness = grid_status['greenness']
        
        pending_jobs = self.job_queue.get_prioritized_queue()
        scheduled_jobs = []
        deferred_jobs = []
        
        for job in pending_jobs:
            if carbon_intensity < job.carbon_intensity_threshold:
                # Green enough - schedule job
                self.job_queue.update_job_status(job.job_id, JobStatus.SCHEDULED.value)
                self.job_queue.update_job(
                    job.job_id,
                    scheduled_for=datetime.now().isoformat()
                )
                scheduled_jobs.append(job)
            else:
                # Too dirty - defer job
                self.job_queue.update_job_status(job.job_id, JobStatus.DEFERRED.value)
                
                # Find optimal time using forecast
                try:
                    optimal_time, optimal_ci = get_best_start_time(
                        duration_minutes=job.duration_minutes,
                        region=region,
                        max_window_hours=24
                    )
                    self.job_queue.update_job(
                        job.job_id,
                        scheduled_for=optimal_time.isoformat()
                    )
                except Exception:
                    # Fallback: schedule for 6 hours later
                    reschedule_time = datetime.now() + timedelta(hours=6)
                    self.job_queue.update_job(
                        job.job_id,
                        scheduled_for=reschedule_time.isoformat()
                    )
                
                deferred_jobs.append(job)
        
        # Calculate estimated emissions savings
        total_avoided = sum(
            self.job_queue.calculate_emissions_for_job(j, carbon_intensity) -
            self.job_queue.calculate_emissions_for_job(j, 200)  # Assume optimal is ~200
            for j in deferred_jobs
        )
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'region': region,
            'current_carbon_intensity': carbon_intensity,
            'grid_greenness': greenness,
            'scheduled_count': len(scheduled_jobs),
            'deferred_count': len(deferred_jobs),
            'estimated_emissions_saved_kg': max(0, total_avoided),
            'scheduled_jobs': [asdict(j) for j in scheduled_jobs],
            'deferred_jobs': [asdict(j) for j in deferred_jobs]
        }
        
        self.schedule_history.append(result)
        return result
    
    def schedule_single_job(
        self,
        job: GPUJob,
        region: str = "GB",
        max_window_hours: int = 24
    ) -> Dict:
        """
        Schedule a single job and return detailed scheduling info.
        
        Returns comprehensive info including comparison with running now.
        """
        # Get current vs optimal comparison
        now_window, optimal_window = get_current_vs_optimal(
            duration_minutes=job.duration_minutes,
            region=region,
            max_window_hours=max_window_hours
        )
        
        # Calculate emissions
        power_kw = job.power_draw_watts / 1000
        duration_h = job.duration_minutes / 60
        
        emissions_now = power_kw * duration_h * (now_window.value / 1000)
        emissions_optimal = power_kw * duration_h * (optimal_window.value / 1000)
        savings_kg = emissions_now - emissions_optimal
        savings_percent = (savings_kg / emissions_now * 100) if emissions_now > 0 else 0
        
        # Update job
        self.job_queue.update_job(
            job.job_id,
            scheduled_for=optimal_window.start.isoformat(),
            status=JobStatus.SCHEDULED.value
        )
        
        return {
            'job_id': job.job_id,
            'job_name': job.name,
            'duration_minutes': job.duration_minutes,
            'region': region,
            
            # Now window info
            'ci_now': now_window.value,
            'emissions_now_g': emissions_now * 1000,
            
            # Optimal window info
            'optimal_time': optimal_window.start,
            'ci_optimal': optimal_window.value,
            'emissions_optimal_g': emissions_optimal * 1000,
            
            # Savings
            'savings_g': savings_kg * 1000,
            'savings_percent': savings_percent,
            
            # Delay
            'delay_hours': (optimal_window.start - datetime.now(timezone.utc)).total_seconds() / 3600
        }
    
    def run_scheduled_job(self, job_id: str) -> Dict:
        """Execute a scheduled job and track emissions."""
        job = self.job_queue.get_job(job_id)
        
        if not job:
            return {'error': 'Job not found'}
        
        if job.status != JobStatus.SCHEDULED.value:
            return {'error': f'Job is not scheduled (status: {job.status})'}
        
        # Update status to running
        self.job_queue.update_job_status(job_id, JobStatus.RUNNING.value)
        
        # Start emissions tracking
        self.emissions_tracker.start_tracking(job.name)
        
        # Simulate job execution
        # In real scenario, this would actually run the GPU workload
        simulation_time = min(5, job.duration_minutes / 10)
        time.sleep(simulation_time)
        
        # Stop tracking and get emissions
        emissions_record = self.emissions_tracker.stop_tracking()
        
        # Update job with emissions data
        self.job_queue.update_job(
            job_id,
            emissions_kg_co2=emissions_record.get('emissions_kg_co2', 0),
            status=JobStatus.COMPLETED.value
        )
        
        return {
            'job_id': job_id,
            'status': 'completed',
            'emissions_kg_co2': emissions_record.get('emissions_kg_co2', 0),
            'duration_seconds': emissions_record.get('duration_seconds', 0)
        }
    
    def get_dashboard_stats(self) -> Dict:
        """Get comprehensive stats for dashboard display."""
        queue_stats = self.job_queue.get_queue_stats()
        emissions_summary = self.emissions_tracker.get_emissions_summary()
        
        return {
            'total_jobs_submitted': queue_stats['total'],
            'pending': queue_stats['pending'],
            'scheduled': queue_stats['scheduled'],
            'running': queue_stats['running'],
            'completed': queue_stats['completed'],
            'deferred': queue_stats['deferred'],
            
            'total_emissions_kg': emissions_summary['total_emissions_kg'],
            'avg_job_emissions_kg': emissions_summary['avg_emissions_per_job_kg'],
            'total_duration_hours': emissions_summary['total_duration_hours'],
            
            'schedule_history': self.schedule_history[-10:]  # Last 10
        }
    
    def get_forecast_data(self, region: str = "GB", hours: int = 24) -> List[Dict]:
        """Get forecast data formatted for charts."""
        forecast = generate_mock_forecast(region=region, hours=hours)
        return [
            {
                'datetime': point.datetime,
                'value': point.value,
                'region': region
            }
            for point in forecast
        ]


# Export singleton
scheduler = CarbonAwareScheduler()
