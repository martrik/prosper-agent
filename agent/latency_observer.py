import time
from loguru import logger
from pipecat.frames.frames import BotStartedSpeakingFrame, UserStoppedSpeakingFrame
from pipecat.observers.base_observer import BaseObserver


class LatencyMetricsCollector:
    def __init__(self):
        self.latencies = []
    
    def add_latency(self, latency: float):
        self.latencies.append(latency)
    
    def get_metrics(self):
        if not self.latencies:
            return None, None, None
        return (
            sum(self.latencies) / len(self.latencies),
            min(self.latencies),
            max(self.latencies)
        )


class CustomLatencyObserver(BaseObserver):
    def __init__(self, metrics_collector: LatencyMetricsCollector):
        super().__init__()
        self.metrics_collector = metrics_collector
        self.user_stop_time = None
    
    async def on_push_frame(self, data):
        """Called when a frame is pushed through the pipeline"""
        frame = data.frame
        
        if isinstance(frame, UserStoppedSpeakingFrame):
            self.user_stop_time = time.time()
            
        elif isinstance(frame, BotStartedSpeakingFrame):
            if self.user_stop_time:
                latency = time.time() - self.user_stop_time
                self.metrics_collector.add_latency(latency)
                self.user_stop_time = None
            

