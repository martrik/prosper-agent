create table conversation_metrics (
  id bigint primary key generated always as identity,
  conversation_id bigint not null references conversations(id) on delete cascade,
  
  -- Overall metrics
  avg_overall_latency numeric,
  min_overall_latency numeric,
  max_overall_latency numeric,
  
  -- STT metrics
  stt_provider text,
  stt_avg_processing_time numeric,
  stt_min_processing_time numeric,
  stt_max_processing_time numeric,
  stt_avg_ttfb numeric,
  stt_min_ttfb numeric,
  stt_max_ttfb numeric,
  
  -- LLM metrics
  llm_provider text,
  llm_avg_processing_time numeric,
  llm_min_processing_time numeric,
  llm_max_processing_time numeric,
  llm_avg_ttfb numeric,
  llm_min_ttfb numeric,
  llm_max_ttfb numeric,
  
  -- TTS metrics
  tts_provider text,
  tts_avg_processing_time numeric,
  tts_min_processing_time numeric,
  tts_max_processing_time numeric,
  tts_avg_ttfb numeric,
  tts_min_ttfb numeric,
  tts_max_ttfb numeric,
  
  created_at timestamptz default now()
);

-- Create index for faster lookups by conversation_id
create index idx_conversation_metrics_conversation_id on conversation_metrics(conversation_id);

