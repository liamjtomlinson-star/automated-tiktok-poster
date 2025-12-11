"""
Base class for Text-to-Speech providers.

Defines the interface that all TTS implementations must follow.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseTTS(ABC):
    """
    Abstract base class for Text-to-Speech providers.

    All TTS implementations should inherit from this class and implement
    the synthesize method.
    """

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        **kwargs,
    ) -> Path:
        """
        Convert text to speech and save as an audio file.

        Args:
            text: The text to convert to speech.
            output_path: Path where the audio file should be saved.
            **kwargs: Additional provider-specific options.

        Returns:
            Path to the generated audio file.

        Raises:
            TTSError: If synthesis fails.
        """
        pass

    def get_audio_duration(self, audio_path: Path) -> float:
        """
        Get the duration of an audio file in seconds.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Duration in seconds.
        """
        import subprocess
        import json

        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get audio duration: {result.stderr}")

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def estimate_duration(self, text: str, words_per_minute: int = 150) -> float:
        """
        Estimate the audio duration based on text length.

        Args:
            text: The text that will be spoken.
            words_per_minute: Assumed speaking rate.

        Returns:
            Estimated duration in seconds.
        """
        word_count = len(text.split())
        return (word_count / words_per_minute) * 60


class TTSError(Exception):
    """Exception raised when TTS synthesis fails."""

    def __init__(self, message: str, provider: Optional[str] = None):
        self.provider = provider
        super().__init__(f"TTS Error ({provider}): {message}" if provider else message)
