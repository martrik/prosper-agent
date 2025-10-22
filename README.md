# Twilio Chatbot: Inbound

This project is a Pipecat-based chatbot that integrates with Twilio to handle WebSocket connections and provide real-time communication. The project includes FastAPI endpoints for starting a call and handling WebSocket connections.

## Table of Contents

- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Accessing Call Information](#accessing-call-information)

## How It Works

When someone calls your Twilio number:

1. **Twilio attemps to establish a WebSocket connection with your bot**: we use a Twiml Bin to generate the TwiML response that tells Twilio to start a WebSocket stream to your bot
2. **WebSocket connection**: Audio streams between caller and your bot

## Conversation Storage

The bot automatically stores conversation records in Supabase for each agent interaction. The following data is captured:

### Conversations Table

- **Claim ID**: The generated claim number provided to the user
- **Claim Date**: The submission date of the claim
- **Claim Status**: The current status (Pending, Approved, Denied, etc.)
- **Claim Amount**: The monetary amount of the claim
- **State**: The conversation state tracking progress
  - `initial`: Conversation started, claim number provided
  - `ongoing`: User acknowledged claim, data collection in progress
  - `done`: User verified all information, conversation complete
- **Created At**: Timestamp of when the conversation started

### Conversation Metrics Table

Detailed performance metrics are stored in a separate `conversation_metrics` table with a foreign key to the conversation. This includes:

- **Overall Latency**: Average, min, and max end-to-end latency
- **STT Metrics** (Deepgram):
  - Provider name
  - Processing time (avg, min, max)
  - Time to First Byte/TTFB (avg, min, max)
- **LLM Metrics** (OpenAI):
  - Provider name
  - Processing time (avg, min, max)
  - Time to First Byte/TTFB (avg, min, max)
- **TTS Metrics** (Cartesia):
  - Provider name
  - Processing time (avg, min, max)
  - Time to First Byte/TTFB (avg, min, max)

Each piece of information is saved to the database as it's collected during the conversation flow, allowing you to track and analyze all agent interactions and performance metrics per provider.

## Prerequisites

### Twilio

- A Twilio account with:
  - Account SID and Auth Token
  - A purchased phone number that supports voice calls

### AI Services

- OpenAI API key for the LLM inference
- Cartesia API key for speech-to-text and text-to-speech
- Deepgram API key for speech-to-text

### Database

- Supabase project with URL and API key for storing conversation records

### System

- Python 3.10+
- `uv` package manager
- Docker (for production deployment)

## Setup

1. Set up a virtual environment and install dependencies:

   ```sh
   uv sync
   ```

2. Create an .env file and add API keys:

   ```sh
   touch .env
   ```

   Add the following environment variables to your `.env` file:

   ```env
   # AI Service API Keys
   OPENAI_API_KEY=your_openai_api_key_here
   CARTESIA_API_KEY=your_cartesia_api_key_here
   DEEPGRAM_API_KEY=your_deepgram_api_key_here

   # Twilio Configuration
   TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
   TWILIO_AUTH_TOKEN=your_twilio_auth_token_here

   # Supabase Configuration
   SUPABASE_URL=your_supabase_project_url_here
   SUPABASE_KEY=your_supabase_anon_key_here
   ```

3. Set up your Supabase database:

   - Create a Supabase project at [https://supabase.com](https://supabase.com)
   - Run the migration to create the conversations table:
     ```sh
     supabase db push
     ```

## Local Development

`client/server.py` runs a FastAPI server, which the client frontend uses to test the bot without making actual phone calls. Run the server using:

```bash
uv sync
uv run client/server.py
cd client
npm install
npm run dev
```

## Production Deployment

To deploy your twilio-chatbot for inbound calling, we'll use [Pipecat Cloud](https://pipecat.daily.co/).

### Deploy your Bot to Pipecat Cloud

Follow the [quickstart instructions](https://docs.pipecat.ai/getting-started/quickstart#step-2%3A-deploy-to-production) for tips on how to create secrets, build and push a docker image, and deploy your agent to Pipecat Cloud.

### Update Twilio Webhook URL

Update your Twilio phone number's webhook URL to point to your production server instead of ngrok:

- Change from: `https://your-subdomain.ngrok.io/`
- To: `https://your-production-domain.com/`

> Alternatively, you can test your Pipecat Cloud deployment by running your server locally.

### Call your Bot

Place a call to the number associated with your bot. The bot will answer and start the conversation.

## Accessing Call Information in Your Bot

Your bot automatically receives call information through Twilio's `Parameters`. In your `bot.py`, you can access this information from the WebSocket connection. The Pipecat development runner extracts this data using the `parse_telephony_websocket` function. This allows your bot to provide personalized responses based on who's calling and which number they called.
