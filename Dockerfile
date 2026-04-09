# Use Python 3.9+ for zoneinfo support
FROM python:3.9-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application
COPY . .

# Create instance directory for SQLite database
RUN mkdir -p instance

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port 5000
EXPOSE 5000

# Use the entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]
