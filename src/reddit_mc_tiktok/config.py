"""
Configuration management for the Reddit to TikTok video generator.

Handles loading configuration from YAML files and environment variables.
Secrets (API keys, credentials) are loaded exclusively from environment variables.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# Load .env file if present
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class RedditConfig:
    """Reddit API configuration."""

    client_id: str
    client_secret: str
    user_agent: str
    sort_mode: str = "top"
    time_filter: str = "week"
    fetch_limit: int = 25


@dataclass
class FilteringConfig:
    """Story filtering configuration."""

    min_story_length: int = 500
    max_story_length: int = 5000
    allow_nsfw: bool = False
    banned_keywords: list[str] = field(default_factory=list)


@dataclass
class VideoConfig:
    """Video generation configuration."""

    background_video_path: Path
    output_directory: Path
    width: int = 1080
    height: int = 1920
    fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = 23


@dataclass
class TTSConfig:
    """Text-to-speech configuration."""

    provider: str = "local"
    speech_rate: int = 150
    # Local TTS settings
    local_voice_id: str = ""
    local_rate: int = 0
    local_volume: float = 1.0
    # API TTS settings
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    api_voice: str = "default"
    api_format: str = "wav"


@dataclass
class RewriterConfig:
    """Story rewriter configuration."""

    provider: str = "anthropic"
    target_word_count: int = 200
    max_word_count: int = 300
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-haiku-20240307"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"


@dataclass
class SubtitleConfig:
    """Subtitle generation configuration."""

    enabled: bool = True
    font_name: str = "Arial"
    font_size: int = 48
    font_color: str = "FFFFFF"
    outline_color: str = "000000"
    outline_width: int = 3
    margin_bottom: int = 150
    max_chars_per_line: int = 35
    words_per_segment: int = 4


@dataclass
class Config:
    """Main configuration container."""

    subreddits: list[str]
    reddit: RedditConfig
    filtering: FilteringConfig
    video: VideoConfig
    tts: TTSConfig
    rewriter: RewriterConfig
    subtitles: SubtitleConfig
    log_level: str = "INFO"
    log_file: Optional[str] = None


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to the YAML config file. Defaults to config.yaml in project root.

    Returns:
        Config object with all settings loaded.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If required configuration is missing.
    """
    # Determine config file path
    if config_path is None:
        # Look for config.yaml in current directory or parent directories
        current = Path.cwd()
        for path in [current, current.parent, current.parent.parent]:
            candidate = path / "config.yaml"
            if candidate.exists():
                config_path = candidate
                break

    if config_path is None or not config_path.exists():
        raise FileNotFoundError(
            "Configuration file not found. "
            "Please create config.yaml or specify a path with --config."
        )

    # Load YAML configuration
    with open(config_path, "r") as f:
        yaml_config = yaml.safe_load(f)

    logger.info(f"Loaded configuration from {config_path}")

    # Load Reddit credentials from environment (required)
    reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_user_agent = os.getenv(
        "REDDIT_USER_AGENT", "RedditMCTikTok/1.0 (by /u/YourUsername)"
    )

    if not reddit_client_id or not reddit_client_secret:
        raise ValueError(
            "Reddit API credentials not found. "
            "Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables."
        )

    # Build Reddit config
    reddit_yaml = yaml_config.get("reddit", {})
    reddit_config = RedditConfig(
        client_id=reddit_client_id,
        client_secret=reddit_client_secret,
        user_agent=reddit_user_agent,
        sort_mode=reddit_yaml.get("sort_mode", "top"),
        time_filter=reddit_yaml.get("time_filter", "week"),
        fetch_limit=reddit_yaml.get("fetch_limit", 25),
    )

    # Build filtering config
    filter_yaml = yaml_config.get("filtering", {})
    filtering_config = FilteringConfig(
        min_story_length=filter_yaml.get("min_story_length", 500),
        max_story_length=filter_yaml.get("max_story_length", 5000),
        allow_nsfw=filter_yaml.get("allow_nsfw", False),
        banned_keywords=filter_yaml.get("banned_keywords", []),
    )

    # Build video config
    video_yaml = yaml_config.get("video", {})
    video_config = VideoConfig(
        background_video_path=Path(
            video_yaml.get("background_video_path", "assets/minecraft_parkour.mp4")
        ),
        output_directory=Path(video_yaml.get("output_directory", "output")),
        width=video_yaml.get("width", 1080),
        height=video_yaml.get("height", 1920),
        fps=video_yaml.get("fps", 30),
        video_codec=video_yaml.get("video_codec", "libx264"),
        audio_codec=video_yaml.get("audio_codec", "aac"),
        crf=video_yaml.get("crf", 23),
    )

    # Build TTS config
    tts_yaml = yaml_config.get("tts", {})
    local_tts = tts_yaml.get("local", {})
    api_tts = tts_yaml.get("api", {})
    tts_config = TTSConfig(
        provider=tts_yaml.get("provider", "local"),
        speech_rate=tts_yaml.get("speech_rate", 150),
        local_voice_id=local_tts.get("voice_id", ""),
        local_rate=local_tts.get("rate", 0),
        local_volume=local_tts.get("volume", 1.0),
        api_key=os.getenv("TTS_API_KEY"),
        api_url=os.getenv("TTS_API_URL"),
        api_voice=api_tts.get("voice", "default"),
        api_format=api_tts.get("format", "wav"),
    )

    # Build rewriter config
    rewriter_yaml = yaml_config.get("rewriter", {})
    rewriter_config = RewriterConfig(
        provider=rewriter_yaml.get("provider", "anthropic"),
        target_word_count=rewriter_yaml.get("target_word_count", 200),
        max_word_count=rewriter_yaml.get("max_word_count", 300),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_model=rewriter_yaml.get("anthropic_model", "claude-3-haiku-20240307"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=rewriter_yaml.get("openai_model", "gpt-3.5-turbo"),
    )

    # Build subtitle config
    subtitle_yaml = yaml_config.get("subtitles", {})
    subtitle_config = SubtitleConfig(
        enabled=subtitle_yaml.get("enabled", True),
        font_name=subtitle_yaml.get("font_name", "Arial"),
        font_size=subtitle_yaml.get("font_size", 48),
        font_color=subtitle_yaml.get("font_color", "FFFFFF"),
        outline_color=subtitle_yaml.get("outline_color", "000000"),
        outline_width=subtitle_yaml.get("outline_width", 3),
        margin_bottom=subtitle_yaml.get("margin_bottom", 150),
        max_chars_per_line=subtitle_yaml.get("max_chars_per_line", 35),
        words_per_segment=subtitle_yaml.get("words_per_segment", 4),
    )

    # Logging config
    logging_yaml = yaml_config.get("logging", {})

    # Build main config
    config = Config(
        subreddits=yaml_config.get("subreddits", ["AmItheAsshole"]),
        reddit=reddit_config,
        filtering=filtering_config,
        video=video_config,
        tts=tts_config,
        rewriter=rewriter_config,
        subtitles=subtitle_config,
        log_level=logging_yaml.get("level", "INFO"),
        log_file=logging_yaml.get("file", ""),
    )

    return config


def setup_logging(config: Config) -> None:
    """Configure logging based on config settings."""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if config.log_file:
        handlers.append(logging.FileHandler(config.log_file))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def ensure_directories(config: Config) -> None:
    """Create necessary output directories if they don't exist."""
    output_dir = config.video.output_directory

    directories = [
        output_dir,
        output_dir / "audio",
        output_dir / "video",
        output_dir / "scripts",
        output_dir / "subtitles",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")
