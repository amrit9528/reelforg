# ReelForge Deployment & CI/CD Setup

Complete guide for Docker, Docker Compose, and GitHub Actions CI/CD pipeline with self-hosted runner.

## 📋 Quick Links

- **Docker Guide**: [DOCKER_README.md](DOCKER_README.md)
- **CI/CD Setup**: [.github/CI_CD_GUIDE.md](.github/CI_CD_GUIDE.md)
- **Self-Hosted Runner**: [.github/SELF_HOSTED_RUNNER_SETUP.md](.github/SELF_HOSTED_RUNNER_SETUP.md)

## 🚀 Quick Start (5 minutes)

### Option 1: Automated Setup

```bash
bash scripts/quick-start.sh
```

This will:
1. Check Docker/Docker Compose installation
2. Create `.env` file from template
3. Build Docker images
4. Start all services

### Option 2: Manual Setup

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit with your credentials
nano .env  # Add ANTHROPIC_API_KEY, Google OAuth credentials

# 3. Start services
docker-compose up -d

# 4. Access
# Frontend: http://localhost:3000
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## 🐳 Docker Setup

### Services

| Service  | Port | Purpose | Status |
|----------|------|---------|--------|
| Frontend | 3000 | React UI | Health checked |
| API      | 8000 | FastAPI backend | Health checked |
| Nginx    | 80   | Reverse proxy (prod only) | Optional |

### Using Makefile

```bash
# Build images
make build

# Start services
make up

# View logs
make logs-tail

# Shell access
make shell-api

# Stop services
make down

# See all commands
make help
```

### Using Docker Compose Directly

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Health check
docker-compose exec api curl http://localhost:8000/api/status/health
```

## 🔄 GitHub Actions CI/CD

### 1. Configure Repository Secrets

Go to: **Repository > Settings > Secrets**

Add these secrets:

```
ANTHROPIC_API_KEY           # Your Anthropic API key
GOOGLE_OAUTH_CLIENT_ID      # Google OAuth2 client ID
GOOGLE_OAUTH_CLIENT_SECRET  # Google OAuth2 client secret
ALLOWED_ORIGINS             # CORS origins (e.g., https://yourdomain.com)
REACT_APP_API_URL           # API URL visible to frontend
DEPLOY_PATH                 # Path on self-hosted runner
DEPLOY_HOST                 # Self-hosted runner hostname
DEPLOY_USER                 # User on self-hosted runner
DEPLOY_SSH_KEY              # SSH private key for deployments
```

#### Quick Setup with GitHub CLI

```bash
gh secret set ANTHROPIC_API_KEY -b "your-key"
gh secret set GOOGLE_OAUTH_CLIENT_ID -b "your-id"
gh secret set GOOGLE_OAUTH_CLIENT_SECRET -b "your-secret"
# ... repeat for other secrets
```

### 2. Set Up Self-Hosted Runner

Follow the complete guide: [.github/SELF_HOSTED_RUNNER_SETUP.md](.github/SELF_HOSTED_RUNNER_SETUP.md)

Quick summary:

```bash
# 1. SSH into your server
ssh user@your-server.com

# 2. Create runner user
sudo useradd -m -s /bin/bash runner
sudo usermod -aG docker runner

# 3. Download and configure runner
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -o actions-runner-linux-x64-2.xxx.x.tar.gz \
  -L https://github.com/actions/runner/releases/download/v2.xxx.x/actions-runner-linux-x64-2.xxx.x.tar.gz
tar xzf ./actions-runner-linux-x64-2.xxx.x.tar.gz
./config.sh --url https://github.com/YOUR_USERNAME/reelforge \
            --token <GENERATED_TOKEN_FROM_GITHUB>

# 4. Install as service
sudo ./svc.sh install runner
sudo ./svc.sh start
```

### 3. Create GitHub Environments (Optional but Recommended)

Go to: **Repository > Settings > Environments > New environment**

Create "production" environment with environment-specific secrets.

### 4. Workflows

#### CI Workflow (Automatic on Push/PR)

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  - Test backend (Python)
  - Test frontend (Node.js)
  - Build Docker images
```

Triggered automatically. View status in **Actions** tab.

#### Deploy Workflow (Automatic on Push to Main)

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

jobs:
  - Build images
  - Deploy to self-hosted runner
  - Health checks
  - Smoke tests
```

**Manual trigger**:

```bash
gh workflow run deploy.yml
```

## 📊 Monitoring Workflows

### View Workflow Runs

```bash
# List all runs
gh run list

# View specific run
gh run view <run-id>

# Watch in real-time
gh run watch <run-id>

# Get logs
gh run view <run-id> --log
```

### Troubleshooting

```bash
# Enable debug mode
gh secret set ACTIONS_RUNNER_DEBUG -b "true"
gh run rerun <run-id> --debug

# Check runner health
gh api repos/OWNER/REPO/actions/runners | jq '.runners[] | {name, status, busy}'

# View self-hosted runner logs
sudo journalctl -u actions.runner.* -f
```

## 🔐 Security Best Practices

1. **Never commit secrets** - Use GitHub Secrets only
2. **Use dedicated user** - Runner process has limited permissions
3. **Keep runner updated** - GitHub releases updates regularly
4. **SSH key only** - Disable password authentication
5. **Network isolation** - Run runner on private network if possible
6. **Firewall rules** - Only expose necessary ports
7. **Rotate credentials** - Update secrets monthly

## 📁 Directory Structure

```
reelforge/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # CI/CD workflow
│   │   └── deploy.yml                # Deployment workflow
│   ├── CI_CD_GUIDE.md               # CI/CD troubleshooting
│   └── SELF_HOSTED_RUNNER_SETUP.md  # Runner setup guide
├── backend/
│   ├── requirements.txt              # Dev dependencies
│   ├── requirements-prod.txt         # Prod dependencies
│   └── main.py
├── frontend/
│   ├── Dockerfile                    # Frontend image
│   ├── package.json
│   └── src/
├── scripts/
│   └── quick-start.sh               # Quick setup script
├── Dockerfile.backend               # Backend image
├── docker-compose.yml               # Production config
├── docker-compose.override.yml      # Development config
├── .env.example                     # Environment template
├── DOCKER_README.md                 # Docker guide
└── DEPLOYMENT_SETUP.md              # This file
```

## 🛠️ Advanced Configuration

### Custom Domain with HTTPS

1. Get SSL certificates (Let's Encrypt recommended):

```bash
mkdir -p certs
# Place cert.pem and key.pem in certs/
```

2. Update `nginx.conf` with certificate paths

3. Start with production profile:

```bash
docker-compose --profile prod up -d
```

### Database (PostgreSQL)

Add to `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - reelforge

volumes:
  postgres_data:
```

Update API environment:

```
DATABASE_URL=postgresql://user:pass@db:5432/reelforge
```

### Redis Caching

```yaml
services:
  redis:
    image: redis:7-alpine
    networks:
      - reelforge
```

### Environment Variables

Place in `.env`:

```bash
# Development
REACT_APP_ENV=development
DEBUG=True

# Production
REACT_APP_ENV=production
DEBUG=False

# Common
ANTHROPIC_API_KEY=your-key
ALLOWED_ORIGINS=https://yourdomain.com
```

## 📈 Performance Optimization

### Docker Image Size

```bash
# Check layer sizes
docker history reelforge:backend-latest

# Optimize Dockerfile:
# - Use slim base images
# - Multi-stage builds
# - Remove build dependencies
# - Clean package manager cache
```

### Build Speed

```bash
# Use BuildKit
DOCKER_BUILDKIT=1 docker-compose build

# Cache layers properly
# - Put dependencies before code
# - Reuse layers across builds
```

## 🔍 Testing Before Deployment

### Local Testing

```bash
# Test Docker builds
docker-compose build

# Test services start
docker-compose up -d

# Test health checks
make health

# Test API
curl http://localhost:8000/api/status/health

# Test frontend
curl http://localhost:3000
```

### Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Docker images build successfully
- [ ] Services start and are healthy
- [ ] Environment variables configured
- [ ] Secrets added to GitHub
- [ ] Self-hosted runner is online
- [ ] Backup created (if applicable)

## 🚢 Deployment Flow

1. **Push code** to `main` branch
2. **GitHub Actions CI** runs automatically
3. **On CI success**, deployment workflow triggers
4. **Self-hosted runner** builds and deploys
5. **Health checks** verify services are running
6. **Smoke tests** validate functionality

## 📝 Logs and Monitoring

### View Logs

```bash
# Docker Compose logs
docker-compose logs -f api
docker-compose logs -f frontend

# Self-hosted runner logs
sudo journalctl -u actions.runner.* -f

# GitHub Actions logs
gh run view <run-id> --log
```

### Health Monitoring

```bash
# Check service health
docker-compose ps

# Check runner health
gh api repos/OWNER/REPO/actions/runners

# Monitor resource usage
docker stats
```

## 🆘 Troubleshooting

### Services Won't Start

```bash
# Check error logs
docker-compose logs

# Check ports available
lsof -i :8000
lsof -i :3000

# Rebuild images
docker-compose build --no-cache
```

### Deployment Fails

```bash
# SSH to runner
ssh runner@your-server

# Check Docker
docker ps
docker logs reelforge-api

# Check disk space
df -h

# Check memory
free -h
```

### GitHub Actions Errors

See: [.github/CI_CD_GUIDE.md](.github/CI_CD_GUIDE.md#debugging-cicd)

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/reference/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Runner](https://github.com/actions/runner)

## ✅ Completion Checklist

- [ ] Docker Compose setup complete
- [ ] All services build and run locally
- [ ] GitHub Secrets configured
- [ ] Self-hosted runner registered and online
- [ ] CI/CD workflows passing
- [ ] Deployment to self-hosted runner working
- [ ] Health checks passing
- [ ] Documentation reviewed

## 🎯 Next Steps

1. Test Docker setup locally: `bash scripts/quick-start.sh`
2. Set up GitHub Secrets
3. Register self-hosted runner
4. Push to trigger CI/CD
5. Monitor deployment
6. Configure domain and HTTPS
7. Set up backups (if applicable)

---

For detailed information on each component, see the linked documentation files.
