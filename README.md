# MyCards

A simple Flask application for managing cards with SQLite database.

## Prerequisites

- Docker installed on your machine
- Docker Buildx (included with Docker Desktop, or install separately for Linux)
- A Docker registry account (e.g., Docker Hub, GitHub Container Registry) for pushing images

## Docker Commands

### 1. Build the Docker Image

#### Single Architecture (Current Platform)

```bash
docker build -t mycards:latest .
```

#### Multi-Architecture (ARM64 + AMD64)

To build for both ARM (Apple Silicon, AWS Graviton) and AMD (Intel/AMD x86_64) architectures:

**First, create a buildx builder (one-time setup):**

```bash
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```

**Build for multiple platforms:**

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t mycards:latest .
```

> Note: Multi-platform builds without `--push` or `--load` will only build and cache the images. Use `--load` to load a single-platform image locally, or `--push` to push directly to a registry.

### 2. Push to a Docker Registry

#### Tag the image for your registry:

```bash
# For Docker Hub
docker tag mycards:latest <your-dockerhub-username>/mycards:latest

# For GitHub Container Registry
docker tag mycards:latest ghcr.io/<your-github-username>/mycards:latest
```

#### Push single-architecture image:

```bash
# For Docker Hub
docker push <your-dockerhub-username>/mycards:latest

# For GitHub Container Registry
docker push ghcr.io/<your-github-username>/mycards:latest
```

#### Build and push multi-architecture image directly:

```bash
# For Docker Hub
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <your-dockerhub-username>/mycards:latest \
  --push .

# For GitHub Container Registry
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/<your-github-username>/mycards:latest \
  --push .
```

### 3. Run Locally

#### Basic run:

```bash
docker run -p 5000:5000 mycards:latest
```

#### Run with persistent data (recommended):

```bash
docker run -p 5000:5000 -v mycards-data:/app/instance mycards:latest
```

#### Run in detached mode:

```bash
docker run -d -p 5000:5000 -v mycards-data:/app/instance --name mycards mycards:latest
```

#### Stop and remove container:

```bash
docker stop mycards
docker rm mycards
```

Access the application at: http://localhost:5000/cards

### 4. Run Remotely (on a Server)

#### Pull the image on your remote server:

```bash
# For Docker Hub
docker pull <your-dockerhub-username>/mycards:latest

# For GitHub Container Registry
docker pull ghcr.io/<your-github-username>/mycards:latest
```

#### Run on the remote server:

```bash
docker run -d \
  -p 5000:5000 \
  -v mycards-data:/app/instance \
  --name mycards \
  --restart unless-stopped \
  <your-dockerhub-username>/mycards:latest
```

#### Using Docker Compose (recommended for production):

Create a `docker-compose.yml` file on your server:

```yaml
version: '3.8'
services:
  mycards:
    image: <your-dockerhub-username>/mycards:latest
    ports:
      - "5000:5000"
    volumes:
      - mycards-data:/app/instance
    restart: unless-stopped

volumes:
  mycards-data:
```

Then run:

```bash
docker compose up -d
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment mode |
| `SECRET_KEY` | `dev` | Flask secret key (override in production) |

### Setting environment variables:

```bash
docker run -d \
  -p 5000:5000 \
  -e SECRET_KEY=your-secure-secret-key \
  -v mycards-data:/app/instance \
  mycards:latest
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/status` | Health check endpoint |
| GET | `/cards` | View all cards |
| POST | `/cards` | Create a new card |
| POST | `/cards/<id>` | Update a card's timestamp |
| DELETE | `/cards/<id>` | Delete a card |

## Useful Docker Commands

```bash
# View running containers
docker ps

# View logs
docker logs mycards

# Follow logs in real-time
docker logs -f mycards

# Execute a command inside the container
docker exec -it mycards /bin/bash

# View volume data
docker volume inspect mycards-data
```
