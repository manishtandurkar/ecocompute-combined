"""
Core module for EcoCompute AI - Carbon-Aware GPU Scheduler
Combines functionality from ChetanP and ManishHP projects.
"""

from .carbon_api import CarbonDataProvider, carbon_provider
from .carbon_scheduler import CarbonAwareScheduler, scheduler
from .emissions_tracker import GPUEmissionsTracker, tracker
from .job_queue import JobQueue, GPUJob, JobStatus, job_queue
from .forecast import get_best_start_time, generate_mock_forecast

__all__ = [
    'CarbonDataProvider',
    'carbon_provider',
    'CarbonAwareScheduler', 
    'scheduler',
    'GPUEmissionsTracker',
    'tracker',
    'JobQueue',
    'GPUJob',
    'JobStatus',
    'job_queue',
    'get_best_start_time',
    'generate_mock_forecast',
]
