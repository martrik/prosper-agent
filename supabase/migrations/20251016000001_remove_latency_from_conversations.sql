-- Remove latency columns from conversations table since metrics are now in conversation_metrics
alter table conversations 
drop column if exists avg_latency,
drop column if exists min_latency,
drop column if exists max_latency;

