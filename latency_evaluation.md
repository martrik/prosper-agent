# Latency Evaluation

## Offline Evaluation
In order to evaluate the latency of the bot in an automated way, we can use the following approach:

1. Run the bot in a local environment
2. Make a call to the bot
3. Collect the latency metrics
4. Compare the latency metrics with the expected latency metrics

## Online Evaluation
In order to evaluate the latency of the bot online, once the bot is already deployed in production,
we have created a latency observer. This will collect the latencies between the user stops speaking
and the bot starts responding. At the end of each conversation, the min, max and average latencies
are recorded in the conversation row. This way we can easily keep track of our bot's latency
when deployed in production and build alarms and charts around it.

That being said, if I were to make this agent production-ready I wouldn't store the metrics in the
Postgres datbase. Instead I would have a secondary metrics DB (e.g. Prometheus) and store the metrics there.
This would allow us to store more data points and query them more efficiently. Apart from the overall
latency I would also store the latency for each LLM call, each TTS call, each STT call, etc. That would
allow us to easily identify the root cause of any latency issues, or trends over time.
