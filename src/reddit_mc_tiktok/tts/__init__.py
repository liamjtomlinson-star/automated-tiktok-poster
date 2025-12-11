"""
Text-to-Speech module.

Provides pluggable TTS implementations for converting scripts to audio.
"""

from reddit_mc_tiktok.tts.base_tts import BaseTTS
from reddit_mc_tiktok.tts.local_tts import LocalTTS
from reddit_mc_tiktok.tts.api_tts_placeholder import APITTS
from reddit_mc_tiktok.config import TTSConfig


__all__ = ["BaseTTS", "LocalTTS", "APITTS", "get_tts_provider"]


def get_tts_provider(config: TTSConfig) -> BaseTTS:
    """
    Factory function to create the appropriate TTS provider based on config.

    Args:
        config: TTSConfig with provider settings.

    Returns:
        Configured TTS provider instance.
    """
    provider = config.provider.lower()

    if provider == "local":
        return LocalTTS(
            voice_id=config.local_voice_id or None,
            rate=config.local_rate,
            volume=config.local_volume,
        )
    elif provider == "api":
        if not config.api_key or not config.api_url:
            raise ValueError(
                "API TTS provider requires TTS_API_KEY and TTS_API_URL "
                "environment variables to be set."
            )
        return APITTS(
            api_key=config.api_key,
            api_url=config.api_url,
            voice=config.api_voice,
            audio_format=config.api_format,
        )
    else:
        # Default to local
        return LocalTTS()
