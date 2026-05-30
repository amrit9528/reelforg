# Docker & Docker Compose Setup

This guide covers running ReelForge with Docker Compose for both development and production environments.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available for containers

## Quick Start (Development)

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/reelforge.git
cd reelforge
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your credentials:

```bash
ANTHROPIC_API_KEY=your-key
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
```

### 3. Build and Start Services

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Access Services

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Services Overview

### Backend API (FastAPI)

- **Port**: 8000
- **Health check**: GET `/api/status/health`
- **Docs**: Swagger UI at `/docs`
- **Requirements**: Python 3.12, FFmpeg, yt-dlp

### Frontend (React)

- **Port**: 3000
- **Build**: Multi-stage build for optimized image
- **Server**: Node.js with serve
- **Requirements**: Node 20

### Nginx (Production Only)

- **Port**: 80, 443
- **Profile**: `prod` (use `docker-compose --profile prod up`)
- **Purpose**: Reverse proxy and static file serving

## Development Workflow

### Running Services

```bash
# Start all services in development
docker-compose up

# Start specific service
docker-compose up api
docker-compose up frontend

# Rebuild and start
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f frontend

# Stop services
docker-compose stop

# Remove everything
docker-compose down -v  # -v removes volumes too
```

### Debugging

```bash
# Access container shell
docker-compose exec api bash
docker-compose exec frontend sh

# Run commands in container
docker-compose exec api python -c "import fastapi; print(fastapi.__version__)"

# View real-time logs
docker-compose logs -f --tail=50 api

# Check service status
docker-compose ps

# Inspect network
docker network ls
docker network inspect reelforge_reelforge
```

### Hot Reload (Development)

The containers mount local directories as volumes:

```yaml
volumes:
  - ./backend:/app              # Backend source
  - ./outputs:/app/outputs      # Generated videos
  - ./uploads:/app/uploads      # Uploaded files
```

**Note**: Changes to source code are reflected automatically. Restart containers if needed:

```bash
docker-compose restart api
docker-compose restart frontend
```

## Production Deployment

### With Nginx Reverse Proxy

```bash
# Start with production profile (includes Nginx)
docker-compose --profile prod up -d

# This exposes:
# - Port 80 (HTTP)
# - Port 443 (HTTPS with certs)
```

### Environment Configuration

Create `.env` for production:

```bash
COMPOSE_PROJECT_NAME=reelforge-prod
ANTHROPIC_API_KEY=prod-key
GOOGLE_OAUTH_CLIENT_ID=prod-id
GOOGLE_OAUTH_CLIENT_SECRET=prod-secret
ALLOWED_ORIGINS=https://yourdomain.com
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_ENV=production
```

### SSL/TLS Setup

Place certificates in `./certs/`:

```bash
mkdir -p certs
cp /path/to/cert.pem certs/
cp /path/to/key.pem certs/
```

Update `nginx.conf` with certificate paths.

### Resource Limits

Add resource limits to `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Troubleshooting

### Container Fails to Start

```bash
# Check logs
docker-compose logs api

# Common issues:
# - Port already in use: Change ports in docker-compose.yml
# - Missing environment variables: Check .env file
# - Out of memory: Increase Docker memory limits
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000
lsof -i :3000

# Or change ports in docker-compose.yml
ports:
  - "8001:8000"  # Host:Container
  - "3001:3000"
```

### Health Check Failing

```bash
# Check specific service health
docker-compose exec api curl -f http://localhost:8000/api/status/health

# View health check logs
docker inspect reelforge-api --format='{{json .State.Health}}' | jq
```

### Build Issues

```bash
# Clear build cache
docker-compose build --no-cache

# Force rebuild
docker-compose up --build --force-recreate

# Remove all images
docker image prune -a
```

## Useful Commands

```bash
# Show all containers and images
docker ps -a
docker images

# View resource usage
docker stats

# Clean up unused resources
docker system prune -a

# Save/Load images
docker save reelforge:backend-latest > image.tar
docker load < image.tar

# Push to registry (for CI/CD)
docker tag reelforge:backend myregistry/reelforge:backend
docker push myregistry/reelforge:backend
```

## Docker Compose Profiles

Profiles allow running different service combinations:

```bash
# Production (with Nginx)
docker-compose --profile prod up

# Development (without Nginx)
docker-compose up

# Specific services
docker-compose up api frontend  # Skip Nginx
```

## Performance Optimization

### Build Cache

```bash
# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker-compose build

# Multi-stage builds reduce final image size
# Backend: 3.2GB -> 1.2GB (with slim base image)
# Frontend: 500MB -> 200MB (with multi-stage build)
```

### Image Size

```bash
# View image layers
docker history reelforge:backend-latest

# Optimize by:
# - Using slim/alpine base images
# - Removing build dependencies
# - Minimizing layers
# - Cleaning package manager cache
```

## Monitoring

### Container Logs

```bash
# Aggregate logs
docker-compose logs -f --timestamps

# Specific service
docker-compose logs -f api --tail=100

# Export logs
docker-compose logs > logs.txt
```

### Health Checks

```bash
# Monitor health
watch 'docker-compose ps'

# Check health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## CI/CD Integration

GitHub Actions workflows automatically:

1. Run tests on push to `main`/`develop`
2. Build Docker images
3. Deploy to self-hosted runner on merge to `main`

See `.github/workflows/` for configuration.

## Next Steps

- Set up self-hosted runner: See `.github/SELF_HOSTED_RUNNER_SETUP.md`
- Configure CI/CD: See `.github/workflows/`
- Deploy to production: Use `docker-compose --profile prod up`
