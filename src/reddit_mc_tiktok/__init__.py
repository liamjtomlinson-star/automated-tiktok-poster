"""
Reddit to TikTok Video Generator

A command-line tool that automates creating TikTok-style vertical videos
from Reddit stories with background footage.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from reddit_mc_tiktok.models import Story, GeneratedVideo
from reddit_mc_tiktok.config import Config, load_config

__all__ = [
    "Story",
    "GeneratedVideo",
    "Config",
    "load_config",
    "__version__",
]
