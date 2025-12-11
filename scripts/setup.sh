#!/bin/bash
# Setup script for Reddit to TikTok Video Generator
# Creates virtual environment and installs dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Reddit to TikTok Video Generator - Setup"
echo "========================================"
echo ""

cd "$PROJECT_DIR"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Install with: brew install python@3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "Warning: ffmpeg is not installed."
    echo "Install with: brew install ffmpeg"
    echo ""
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo ""
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Install the package in development mode
echo ""
echo "Installing package in development mode..."
pip install -e .

# Create .env from example if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo ""
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env and add your API credentials."
fi

# Create output directories
echo ""
echo "Creating output directories..."
mkdir -p output/audio output/video output/scripts output/subtitles

echo ""
echo "========================================"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your Reddit API credentials"
echo "  2. Edit config.yaml to customize settings"
echo "  3. Add your background video to assets/minecraft_parkour.mp4"
echo "  4. Run: source venv/bin/activate"
echo "  5. Run: python -m reddit_mc_tiktok --help"
echo ""
