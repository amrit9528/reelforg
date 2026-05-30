.PHONY: help build up down logs shell test clean

help:
	@echo "ReelForge Docker Commands"
	@echo "========================="
	@echo ""
	@echo "Build:"
	@echo "  make build              - Build all Docker images"
	@echo "  make build-api          - Build only backend API image"
	@echo "  make build-frontend     - Build only frontend image"
	@echo ""
	@echo "Services:"
	@echo "  make up                 - Start all services in background"
	@echo "  make down               - Stop all services"
	@echo "  make restart            - Restart all services"
	@echo "  make restart-api        - Restart API service"
	@echo "  make restart-frontend   - Restart frontend service"
	@echo ""
	@echo "Logs:"
	@echo "  make logs               - Show logs from all services"
	@echo "  make logs-api           - Show logs from API"
	@echo "  make logs-frontend      - Show logs from frontend"
	@echo "  make logs-tail          - Follow logs (Ctrl+C to stop)"
	@echo ""
	@echo "Development:"
	@echo "  make shell-api          - Access API container shell"
	@echo "  make shell-frontend     - Access frontend container shell"
	@echo "  make test               - Run tests"
	@echo "  make lint               - Run linting checks"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean              - Stop services and remove containers"
	@echo "  make clean-all          - Clean + remove volumes and images"
	@echo ""
	@echo "Production:"
	@echo "  make prod-up            - Start with production profile (includes Nginx)"
	@echo "  make prod-down          - Stop production services"
	@echo ""

# Build targets
build:
	docker-compose build

build-api:
	docker-compose build api

build-frontend:
	docker-compose build frontend

# Service management
up:
	docker-compose up -d
	@echo "Services started. Access them at:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

down:
	docker-compose down

restart:
	docker-compose restart

restart-api:
	docker-compose restart api

restart-frontend:
	docker-compose restart frontend

# Logging
logs:
	docker-compose logs

logs-api:
	docker-compose logs api

logs-frontend:
	docker-compose logs frontend

logs-tail:
	docker-compose logs -f

# Development
shell-api:
	docker-compose exec api bash

shell-frontend:
	docker-compose exec frontend sh

test:
	docker-compose exec api python -m pytest tests/ -v

lint:
	docker-compose exec api flake8 .
	docker-compose exec api black --check .

# Cleanup
clean:
	docker-compose down --remove-orphans

clean-all:
	docker-compose down -v --remove-orphans
	docker image prune -f

# Production
prod-up:
	docker-compose --profile prod up -d
	@echo "Production services started with Nginx reverse proxy"
	@echo "  HTTP: http://localhost"
	@echo "  HTTPS: https://localhost (if certificates configured)"

prod-down:
	docker-compose --profile prod down

# Status
status:
	docker-compose ps

health:
	@docker-compose exec api curl -f http://localhost:8000/api/status/health && echo "\n✅ API is healthy" || echo "\n❌ API health check failed"

# Environment setup
env-setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env file created from .env.example"; \
		echo "⚠️  Please update .env with your credentials"; \
	else \
		echo "✅ .env file already exists"; \
	fi

# Full setup
setup: env-setup build up
	@echo ""
	@echo "✅ ReelForge is ready!"
	@echo "🌐 Frontend: http://localhost:3000"
	@echo "🔌 API: http://localhost:8000"
	@echo "📚 Docs: http://localhost:8000/docs"

.PHONY: help build build-api build-frontend up down restart restart-api restart-frontend logs logs-api logs-frontend logs-tail shell-api shell-frontend test lint clean clean-all prod-up prod-down status health env-setup setup
