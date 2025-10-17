# Prosper Server

This directory contains the Twilio webhook server that handles incoming calls and WebSocket connections.

## Dependencies

The server has its own `pyproject.toml` with separated dependencies:

### Production Dependencies (minimal)
- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **python-dotenv** - Environment variable management
- **twilio** - Twilio SDK for TwiML generation

### Dev Dependencies (for local bot testing)
- **pipecat-ai** and related packages - For bot functionality
- **supabase** - Database client
- **python-dateutil** - Date parsing
- **loguru** - Logging
- **aiofiles** - Async file operations

The bot/agent dependencies are only needed for local development. In production, Pipecat Cloud handles the bot logic.

## Docker Build

### Production (minimal dependencies)
```bash
docker build -t prosper-server .
```

### Development (with bot dependencies)
```bash
docker build -t prosper-server --build-arg DEV=true .
```

## Local Development

To run the server locally with dev dependencies:

```bash
cd server
uv sync --dev
uv run python server.py
```

