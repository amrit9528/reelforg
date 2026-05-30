# Self-Hosted Runner Setup Guide

This guide will help you set up a self-hosted GitHub Actions runner for ReelForge deployments.

## Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Docker & Docker Compose installed
- Git installed
- SSH access to the server
- GitHub repository with appropriate permissions

## Step 1: Create Runner User

```bash
# SSH into your server
ssh user@your-server.com

# Create dedicated user for runner
sudo useradd -m -s /bin/bash runner
sudo usermod -aG docker runner
sudo usermod -aG sudo runner

# Switch to runner user
sudo su - runner
```

## Step 2: Download and Configure Runner

```bash
# Go to your GitHub repository
# Navigate to: Settings > Actions > Runners > New self-hosted runner

# Create directory for runner
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download the latest runner package (check GitHub for latest version)
curl -o actions-runner-linux-x64-2.xxx.x.tar.gz -L https://github.com/actions/runner/releases/download/v2.xxx.x/actions-runner-linux-x64-2.xxx.x.tar.gz

# Extract
tar xzf ./actions-runner-linux-x64-2.xxx.x.tar.gz

# Create configuration
./config.sh --url https://github.com/YOUR_USERNAME/reelforge \
            --token <GENERATED_TOKEN_FROM_GITHUB> \
            --name reelforge-runner \
            --labels self-hosted,reelforge \
            --work _work
```

## Step 3: Install Runner Service

```bash
# Install as a service (recommended)
sudo ./svc.sh install runner

# Start the service
sudo ./svc.sh start

# Check status
sudo ./svc.sh status

# View logs
sudo journalctl -u actions.runner.* -f
```

## Step 4: Configure SSH Key for Deployments

```bash
# Generate SSH key if not exists
ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N ""

# Add public key to your deployment server's authorized_keys
cat ~/.ssh/github_actions.pub

# Store private key as GitHub secret:
# Go to: Repository > Settings > Secrets > New repository secret
# Name: DEPLOY_SSH_KEY
# Value: <contents of ~/.ssh/github_actions>
```

## Step 5: Set Up Deployment Directory

```bash
# Create deployment directory
sudo mkdir -p /home/reelforge/reelforge
sudo chown runner:runner /home/reelforge/reelforge

# Clone repository
cd /home/reelforge/reelforge
git clone https://github.com/YOUR_USERNAME/reelforge.git .
```

## Step 6: Configure Environment Variables

```bash
# Create environment file directory
mkdir -p ~/.reelforge

# Create production environment file
cat > ~/.reelforge/.env.production << 'EOF'
ANTHROPIC_API_KEY=your-key-here
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
ALLOWED_ORIGINS=https://your-domain.com
REACT_APP_API_URL=https://api.your-domain.com
EOF

chmod 600 ~/.reelforge/.env.production
```

## Step 7: Add GitHub Secrets

Go to: Repository > Settings > Secrets and add:

```
DEPLOY_PATH=/home/reelforge/reelforge
DEPLOY_HOST=your-server.com
DEPLOY_USER=runner
ANTHROPIC_API_KEY=<your-key>
GOOGLE_OAUTH_CLIENT_ID=<your-id>
GOOGLE_OAUTH_CLIENT_SECRET=<your-secret>
ALLOWED_ORIGINS=https://your-domain.com
REACT_APP_API_URL=https://api.your-domain.com
```

## Step 8: Configure Firewall (if applicable)

```bash
# Allow ports for services
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # API (if exposing)
sudo ufw allow 3000/tcp  # Frontend (if exposing)

# Or use Docker networking (recommended)
# Services communicate via Docker bridge network
```

## Step 9: Test the Runner

### Trigger a test workflow

```bash
# Create a simple test workflow
cat > .github/workflows/test-runner.yml << 'EOF'
name: Test Runner

on: workflow_dispatch

jobs:
  test:
    runs-on: [self-hosted, reelforge]
    steps:
      - uses: actions/checkout@v4
      - name: Test
        run: |
          echo "Runner is working!"
          docker ps
          docker-compose --version
EOF

# Push and trigger from GitHub UI
```

## Monitoring & Maintenance

### Check runner status in GitHub

Navigate to: Repository > Settings > Actions > Runners

You should see your runner as "Idle" when not running jobs.

### Monitor logs

```bash
# Runner service logs
sudo journalctl -u actions.runner.* -f

# Docker logs
docker logs -f reelforge-api
docker logs -f reelforge-frontend
```

### Troubleshooting

```bash
# Check runner process
ps aux | grep runner

# Restart runner service
sudo ./svc.sh restart

# Check Docker daemon
docker ps

# Verify runner configuration
cat ~/actions-runner/.runner
```

## Scaling to Multiple Runners

For high-volume deployments, set up multiple runners:

```bash
# Repeat Steps 1-3 with different names:
./config.sh --url https://github.com/YOUR_USERNAME/reelforge \
            --token <TOKEN> \
            --name reelforge-runner-2 \
            --labels self-hosted,reelforge,runner-2
```

Update workflow to use different runners:

```yaml
runs-on: [self-hosted, reelforge, runner-2]
```

## Security Best Practices

1. **Use dedicated user account** - Never use root
2. **Enable SSH key authentication** - Disable password auth
3. **Firewall properly** - Only expose necessary ports
4. **Rotate secrets regularly** - Use GitHub secrets management
5. **Keep runner updated** - Update runner software regularly
6. **Monitor logs** - Set up log aggregation/alerting
7. **Use network isolation** - Run on private network if possible

## Docker Resource Limits

Create `~/.docker/daemon.json` to limit resource usage:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "insecure-registries": []
}
```

Then restart Docker:

```bash
sudo systemctl restart docker
```

## Auto-Cleanup Script

Create a cleanup script for old images:

```bash
cat > ~/cleanup-docker.sh << 'EOF'
#!/bin/bash
# Remove dangling images
docker image prune -f --filter "dangling=true"

# Remove images older than 30 days
docker image prune -f --filter "until=720h"

# Remove stopped containers
docker container prune -f
EOF

chmod +x ~/cleanup-docker.sh

# Add to crontab
crontab -e
# Add: 0 2 * * 0 ~/cleanup-docker.sh
```

## Next Steps

1. Push code to your repository
2. GitHub Actions will automatically trigger CI workflow
3. On merge to `main`, deployment workflow runs on self-hosted runner
4. Monitor in GitHub Actions tab for status and logs
