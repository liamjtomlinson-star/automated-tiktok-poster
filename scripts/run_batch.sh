#!/bin/bash
# Run batch video generation
# Usage: ./scripts/run_batch.sh [--limit <n>] [--subreddit <name>]

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

# Run the batch command
if [ $# -eq 0 ]; then
    # Default: generate 5 videos
    echo "Running batch video generation (5 videos from configured subreddits)..."
    python -m reddit_mc_tiktok batch --limit 5
else
    echo "Running batch video generation with arguments: $@"
    python -m reddit_mc_tiktok batch "$@"
fi
