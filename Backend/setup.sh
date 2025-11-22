#!/bin/bash

echo "🚀 Setting up ElevenLabs AI Agent Project"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your ELEVENLABS_API_KEY"
    echo "   Get your API key from: https://elevenlabs.io/app/settings/api-keys"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Create virtual environment if it doesn't exist
if [ ! -d "../.venv" ]; then
    echo "📦 Creating virtual environment..."
    cd .. && python3 -m venv .venv && cd Backend
    echo "✓ Virtual environment created"
    echo ""
else
    echo "✓ Virtual environment already exists"
    echo ""
fi

# Activate virtual environment and install dependencies
echo "📥 Installing dependencies..."
source ../.venv/bin/activate
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your ELEVENLABS_API_KEY"
echo "2. Run: python3 elevenLabs.py (to create the agent)"
echo "3. Run: python3 chat_with_agent.py (to test the agent)"
echo ""
echo "Note: Make sure cleaned_output.html exists in this directory"
echo ""
