#!/bin/bash

# ReelForge Quick Start Script
# This script sets up and starts ReelForge with Docker Compose

set -e

echo "🚀 ReelForge Quick Start"
echo "======================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Setup .env file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your credentials:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GOOGLE_OAUTH_CLIENT_ID"
    echo "   - GOOGLE_OAUTH_CLIENT_SECRET"
    echo ""
    read -p "Press Enter once you've updated .env..."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
    echo ""
    echo "📍 Access your services at:"
    echo "   🌐 Frontend: http://localhost:3000"
    echo "   🔌 Backend API: http://localhost:8000"
    echo "   📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs:      docker-compose logs -f"
    echo "   Stop services:  docker-compose down"
    echo "   Restart:        docker-compose restart"
    echo "   Shell access:   docker-compose exec api bash"
    echo ""
    echo "✨ Happy coding!"
else
    echo "❌ Services failed to start. Check logs with: docker-compose logs"
    exit 1
fi
