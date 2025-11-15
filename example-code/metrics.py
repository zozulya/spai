"""
Metrics Collection System

Tracks pipeline performance and saves to JSON files for analysis.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from time import time


class MetricsCollector:
    """Collects and saves pipeline metrics"""
    
    def __init__(self, config: Dict, run_id: str):
        self.config = config
        self.run_id = run_id
        self.started_at = datetime.utcnow()
        
        # Phase timings
        self.phase_timings = {}
        self.current_phase = None
        self.phase_start = None
        
        # Metrics data
        self.metrics = {
            'run_id': run_id,
            'started_at': self.started_at.isoformat() + 'Z',
            'environment': config.get('environment', 'unknown'),
            'phases': {}
        }
        
        # Output directory
        metrics_config = config.get('metrics', {})
        self.output_dir = Path(metrics_config.get('output', 'output/metrics'))
        self.enabled = metrics_config.get('enabled', True)
    
    def start_phase(self, phase_name: str):
        """Start timing a phase"""
        self.current_phase = phase_name
        self.phase_start = time()
        
        if phase_name not in self.metrics['phases']:
            self.metrics['phases'][phase_name] = {
                'duration_seconds': 0,
                'data': {}
            }
    
    def end_phase(self, phase_name: str, data: Optional[Dict] = None):
        """End timing a phase and record data"""
        if self.current_phase != phase_name:
            return
        
        duration = time() - self.phase_start
        self.metrics['phases'][phase_name]['duration_seconds'] = duration
        
        if data:
            self.metrics['phases'][phase_name]['data'].update(data)
        
        self.current_phase = None
        self.phase_start = None
    
    def record_cost(self, cost_usd: float):
        """Record LLM cost"""
        if 'costs' not in self.metrics:
            self.metrics['costs'] = {
                'total_usd': 0,
                'llm_calls': 0
            }
        
        self.metrics['costs']['total_usd'] += cost_usd
        self.metrics['costs']['llm_calls'] += 1
    
    def record_error(self, error_type: str):
        """Record an error"""
        if 'errors' not in self.metrics:
            self.metrics['errors'] = {}
        
        if error_type not in self.metrics['errors']:
            self.metrics['errors'][error_type] = 0
        
        self.metrics['errors'][error_type] += 1
    
    def get_total_duration(self) -> float:
        """Get total elapsed time in seconds"""
        return (datetime.utcnow() - self.started_at).total_seconds()
    
    def save(self, final_data: Optional[Dict] = None):
        """Save metrics to JSON file"""
        if not self.enabled:
            return
        
        # Add final data
        self.metrics['ended_at'] = datetime.utcnow().isoformat() + 'Z'
        self.metrics['duration_seconds'] = self.get_total_duration()
        
        if final_data:
            self.metrics.update(final_data)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save per-run metrics
        run_file = self.output_dir / f"{self.run_id}.json"
        with open(run_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        
        # Update summary
        self._update_summary()
    
    def _update_summary(self):
        """Update rolling summary file"""
        summary_file = self.output_dir / 'summary.json'
        
        # Load existing summary
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
        else:
            summary = {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'total_articles': 0,
                'total_cost_usd': 0,
                'last_30_runs': []
            }
        
        # Update summary
        summary['total_runs'] += 1
        
        if self.metrics.get('status') == 'success':
            summary['successful_runs'] += 1
        else:
            summary['failed_runs'] += 1
        
        stats = self.metrics.get('stats', {})
        summary['total_articles'] += stats.get('published', 0)
        
        costs = self.metrics.get('costs', {})
        summary['total_cost_usd'] += costs.get('total_usd', 0)
        
        # Add to recent runs (keep last 30)
        run_summary = {
            'run_id': self.run_id,
            'timestamp': self.metrics['started_at'],
            'status': self.metrics.get('status', 'unknown'),
            'articles_published': stats.get('published', 0),
            'cost_usd': costs.get('total_usd', 0)
        }
        
        summary['last_30_runs'].insert(0, run_summary)
        summary['last_30_runs'] = summary['last_30_runs'][:30]
        
        # Save updated summary
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
