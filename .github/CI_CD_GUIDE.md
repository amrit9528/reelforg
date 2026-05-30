# CI/CD Guide

This guide covers the GitHub Actions CI/CD pipeline for ReelForge.

## Overview

The CI/CD pipeline consists of three workflows:

1. **CI (ci.yml)** - Runs on every push/PR
   - Tests backend (Python)
   - Tests frontend (Node.js)
   - Builds Docker images

2. **Deploy (deploy.yml)** - Runs on push to main
   - Builds Docker images
   - Deploys to self-hosted runner
   - Runs health checks

## Workflows

### 1. CI Workflow (Continuous Integration)

**Trigger**: Push to main/develop, Pull Requests

**Jobs**:
- `test-backend`: Tests Python code with pytest
- `test-frontend`: Builds React frontend
- `build-docker`: Builds Docker images

```bash
# Manually trigger (if needed)
gh workflow run ci.yml -f branch=main
```

### 2. Deployment Workflow

**Trigger**: Push to main branch (automatic), or manually via workflow_dispatch

**Jobs**:
- Stops existing containers
- Builds new images
- Starts services
- Runs health checks
- Verifies deployment

**Manual trigger**:
```bash
gh workflow run deploy.yml -f environment=production
```

## Secrets Configuration

Required GitHub Secrets (Repository Settings > Secrets):

```
ANTHROPIC_API_KEY          - Your Anthropic API key
GOOGLE_OAUTH_CLIENT_ID     - Google OAuth2 client ID
GOOGLE_OAUTH_CLIENT_SECRET - Google OAuth2 client secret
ALLOWED_ORIGINS            - CORS allowed origins (default: http://localhost:3000)
REACT_APP_API_URL          - Frontend API URL
DEPLOY_PATH                - Path on self-hosted runner (default: /home/reelforge/reelforge)
DEPLOY_HOST                - Self-hosted runner hostname
DEPLOY_USER                - User account on self-hosted runner
DEPLOY_SSH_KEY             - SSH private key for deployments
```

### Adding Secrets

```bash
# Via GitHub CLI
gh secret set ANTHROPIC_API_KEY -b "your-key"
gh secret set GOOGLE_OAUTH_CLIENT_ID -b "your-id"
gh secret set GOOGLE_OAUTH_CLIENT_SECRET -b "your-secret"

# Or via GitHub UI:
# Repository > Settings > Secrets > New repository secret
```

## Workflow Status

### View Workflow Runs

```bash
# List all workflow runs
gh run list

# View specific workflow run
gh run view <run-id>

# Watch workflow in real-time
gh run watch <run-id>

# View logs for a job
gh run view <run-id> --log
```

### Troubleshooting Failed Runs

```bash
# Get detailed error info
gh run view <run-id> --log --jq '.jobs[] | select(.conclusion=="failure")'

# Rerun a failed workflow
gh run rerun <run-id> --failed
```

## Setting Up Environments

GitHub Environments allow different secrets per environment:

```bash
# Create production environment in GitHub UI:
# Settings > Environments > New environment > production

# Add environment-specific secrets:
# Environment > production > Add secret > DEPLOY_PATH=/home/reelforge/reelforge
```

Update workflow to use environment:

```yaml
jobs:
  deploy:
    environment: production
    runs-on: [self-hosted, reelforge]
```

## Runner Configuration

### Self-Hosted Runner Labels

The deployment workflow runs on runners with these labels:
- `self-hosted` - GitHub's default label
- `reelforge` - Custom label we set during registration

To target specific runners:

```yaml
runs-on: [self-hosted, reelforge, linux]
```

To see available runners:

```bash
gh api repos/OWNER/REPO/actions/runners
```

## Debugging CI/CD

### Enable Workflow Debugging

```bash
# Set debug secrets (repo settings):
ACTIONS_STEP_DEBUG=true
ACTIONS_RUNNER_DEBUG=true
```

Then re-run the workflow:

```bash
gh run rerun <run-id> --debug
```

### Check Logs

```bash
# View full workflow logs
gh run view <run-id> --log

# Tail logs in real-time
gh run watch <run-id>

# Save logs to file
gh run view <run-id> --log > workflow.log
```

### Common Issues

#### 1. **Authentication Failures**

```bash
# Verify secrets are set correctly
gh secret list

# Check secret value (first 4 chars)
gh secret view ANTHROPIC_API_KEY
```

#### 2. **Docker Image Build Failures**

Check Dockerfile syntax:

```bash
# Build locally to test
docker build -f Dockerfile.backend .
docker build -f frontend/Dockerfile ./frontend
```

#### 3. **Health Check Timeouts**

Increase timeout in workflow:

```yaml
- name: Wait for services
  timeout-minutes: 10  # Increase from default 360 minutes
  run: |
    for i in {1..60}; do
      curl -f http://localhost:8000/api/status/health && break
      sleep 5
    done
```

#### 4. **Port Already in Use**

```bash
# On self-hosted runner
lsof -i :8000
lsof -i :3000

# Or change ports in docker-compose.yml before deployment
```

#### 5. **Out of Disk Space**

```bash
# On self-hosted runner, clean up Docker
docker system prune -a --volumes
```

## Advanced Configuration

### Matrix Testing (Test Multiple Versions)

```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']
    node-version: ['18', '20']

steps:
  - uses: actions/setup-python@v4
    with:
      python-version: ${{ matrix.python-version }}
```

### Conditional Execution

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

### Secrets in Different Contexts

```yaml
# Pass secret to Docker build
- uses: docker/build-push-action@v5
  with:
    build-args: |
      API_KEY=${{ secrets.ANTHROPIC_API_KEY }}
```

### Skip Workflow

Add `[skip ci]` to commit message:

```bash
git commit -m "Update docs [skip ci]"
```

## Notifications

### Slack Integration

1. Go to Slack workspace
2. Create incoming webhook
3. Add webhook URL as secret: `SLACK_WEBHOOK_URL`
4. Add to workflow:

```yaml
- name: Notify Slack
  if: always()
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
      -H 'Content-type: application/json' \
      -d '{"text":"Deployment ${{ job.status }}"}'
```

### Email Notifications

GitHub sends automatic notifications. Configure in:
Repository > Settings > Notifications

## Performance Optimization

### Caching Dependencies

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.12'
    cache: 'pip'

- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
    cache-dependency-path: frontend/package-lock.json
```

### Parallel Jobs

```yaml
jobs:
  test-backend:
    runs-on: ubuntu-latest
    
  test-frontend:
    runs-on: ubuntu-latest

  deploy:
    needs: [test-backend, test-frontend]
    runs-on: [self-hosted, reelforge]
```

Dependencies ensure test jobs run before deploy.

### Build Cache with Docker Buildx

```yaml
- uses: docker/setup-buildx-action@v3

- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## Monitoring and Alerts

### GitHub Status Page

Monitor service status: https://www.githubstatus.com

### Runner Health

```bash
# Check runner status
gh api repos/OWNER/REPO/actions/runners | jq '.runners[] | {name, status, busy}'

# Monitor runner loads
watch 'gh api repos/OWNER/REPO/actions/runners | jq ".runners[].status"'
```

### Workflow Duration

Track workflow execution times:

```bash
gh run list --json conclusion,durationMinutes | tail -10
```

## Best Practices

1. **Keep workflows simple** - One job per workflow file
2. **Use caching** - Cache dependencies and Docker layers
3. **Run in parallel** - Use job dependencies to parallelize
4. **Use environment secrets** - Different secrets per environment
5. **Monitor logs** - Always check workflow logs for warnings
6. **Test locally** - Test Docker builds before committing
7. **Use reusable workflows** - Share workflow logic across repos
8. **Document everything** - Keep workflows readable with comments

## Next Steps

1. Set up GitHub Secrets (see above)
2. Register self-hosted runner (see SELF_HOSTED_RUNNER_SETUP.md)
3. Push code to trigger CI workflow
4. Monitor workflow run
5. Check deployment on self-hosted runner
