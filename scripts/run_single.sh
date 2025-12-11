#!/bin/bash
# Run single video generation
# Usage: ./scripts/run_single.sh [--post-id <id>] [--subreddit <name>]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Run ./scripts/setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Make sure environment variables are set."
fi

# Run the single command
if [ $# -eq 0 ]; then
    # Default: fetch from first configured subreddit
    echo "Running single video generation (using first configured subreddit)..."
    python -m reddit_mc_tiktok single --subreddit AmItheAsshole
else
    echo "Running single video generation with arguments: $@"
    python -m reddit_mc_tiktok single "$@"
fi
