FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

COPY ./server/pyproject.toml pyproject.toml
COPY ./server/uv.lock uv.lock

# Install the project's dependencies using the lockfile and settings
RUN uv sync --locked --no-dev

# Copy the application code
COPY ./server/server.py server.py

# Expose the server port
EXPOSE 7860

# Run the server
CMD ["uv", "run", "python", "server.py"]

