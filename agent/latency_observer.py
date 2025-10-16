import time
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    MetricsFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import (
    ProcessingMetricsData,
    TTFBMetricsData,
)
from pipecat.observers.base_observer import BaseObserver

class ServiceMetrics:
    def __init__(self):
        self.processing_times: List[float] = []
        self.ttfb_times: List[float] = []
    
    def add_processing_time(self, processing_time: float):
        if processing_time > 0:
            self.processing_times.append(processing_time)
    
    def add_ttfb(self, ttfb: float):
        if ttfb > 0:
            self.ttfb_times.append(ttfb)
    
    def get_processing_metrics(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if not self.processing_times:
            return None, None, None
        return (
            sum(self.processing_times) / len(self.processing_times),
            min(self.processing_times),
            max(self.processing_times)
        )
    
    def get_ttfb_metrics(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if not self.ttfb_times:
            return None, None, None
        return (
            sum(self.ttfb_times) / len(self.ttfb_times),
            min(self.ttfb_times),
            max(self.ttfb_times)
        )


class LatencyMetricsCollector:
    def __init__(self, stt_provider: str, llm_provider: str, tts_provider: str):
        self.latencies = []
        self.stt_metrics = ServiceMetrics()
        self.llm_metrics = ServiceMetrics()
        self.tts_metrics = ServiceMetrics()
        self.stt_provider = stt_provider
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider
    
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
    
    def add_metrics_from_frame(self, metrics_frame: MetricsFrame):
        """Process MetricsFrame and add data to appropriate service metrics"""
        for data in metrics_frame.data:
            processor = data.processor
            
            if isinstance(data, ProcessingMetricsData):
                if "STT" in processor or "Deepgram" in processor:
                    self.stt_metrics.add_processing_time(data.value)
                elif "LLM" in processor or "OpenAI" in processor:
                    self.llm_metrics.add_processing_time(data.value)
                elif "TTS" in processor or "Cartesia" in processor:
                    self.tts_metrics.add_processing_time(data.value)
            
            elif isinstance(data, TTFBMetricsData):
                if "STT" in processor or "Deepgram" in processor:
                    self.stt_metrics.add_ttfb(data.value)
                elif "LLM" in processor or "OpenAI" in processor:
                    self.llm_metrics.add_ttfb(data.value)
                elif "TTS" in processor or "Cartesia" in processor:
                    self.tts_metrics.add_ttfb(data.value)
            
    def get_metrics_for_db(self) -> dict:
        """Get all metrics formatted for database storage"""
        avg_overall, min_overall, max_overall = self.get_metrics()
        
        stt_avg_proc, stt_min_proc, stt_max_proc = self.stt_metrics.get_processing_metrics()
        stt_avg_ttfb, stt_min_ttfb, stt_max_ttfb = self.stt_metrics.get_ttfb_metrics()
        
        llm_avg_proc, llm_min_proc, llm_max_proc = self.llm_metrics.get_processing_metrics()
        llm_avg_ttfb, llm_min_ttfb, llm_max_ttfb = self.llm_metrics.get_ttfb_metrics()
        
        tts_avg_proc, tts_min_proc, tts_max_proc = self.tts_metrics.get_processing_metrics()
        tts_avg_ttfb, tts_min_ttfb, tts_max_ttfb = self.tts_metrics.get_ttfb_metrics()
                
        return {
            "avg_overall_latency": avg_overall,
            "min_overall_latency": min_overall,
            "max_overall_latency": max_overall,
            
            "stt_provider": self.stt_provider.value if hasattr(self.stt_provider, 'value') else self.stt_provider,
            "stt_avg_processing_time": stt_avg_proc,
            "stt_min_processing_time": stt_min_proc,
            "stt_max_processing_time": stt_max_proc,
            "stt_avg_ttfb": stt_avg_ttfb,
            "stt_min_ttfb": stt_min_ttfb,
            "stt_max_ttfb": stt_max_ttfb,
            
            "llm_provider": self.llm_provider.value if hasattr(self.llm_provider, 'value') else self.llm_provider,
            "llm_avg_processing_time": llm_avg_proc,
            "llm_min_processing_time": llm_min_proc,
            "llm_max_processing_time": llm_max_proc,
            "llm_avg_ttfb": llm_avg_ttfb,
            "llm_min_ttfb": llm_min_ttfb,
            "llm_max_ttfb": llm_max_ttfb,
            
            "tts_provider": self.tts_provider.value if hasattr(self.tts_provider, 'value') else self.tts_provider,
            "tts_avg_processing_time": tts_avg_proc,
            "tts_min_processing_time": tts_min_proc,
            "tts_max_processing_time": tts_max_proc,
            "tts_avg_ttfb": tts_avg_ttfb,
            "tts_min_ttfb": tts_min_ttfb,
            "tts_max_ttfb": tts_max_ttfb,
        }


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
        
        elif isinstance(frame, MetricsFrame):
            self.metrics_collector.add_metrics_from_frame(frame)
