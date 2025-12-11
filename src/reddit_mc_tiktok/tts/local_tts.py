"""
Local Text-to-Speech implementation using pyttsx3.

This provides offline TTS using the system's built-in speech synthesis.
On macOS, this uses the NSSpeechSynthesizer (Apple's speech synthesis).
"""

import logging
from pathlib import Path
from typing import Optional

from reddit_mc_tiktok.tts.base_tts import BaseTTS, TTSError


logger = logging.getLogger(__name__)


class LocalTTS(BaseTTS):
    """
    Local TTS provider using pyttsx3.

    Uses the system's built-in text-to-speech engine.
    On macOS, this leverages Apple's NSSpeechSynthesizer.
    """

    def __init__(
        self,
        voice_id: Optional[str] = None,
        rate: int = 0,
        volume: float = 1.0,
    ):
        """
        Initialize the local TTS provider.

        Args:
            voice_id: Specific voice to use (system-dependent). None for default.
            rate: Rate adjustment from default (-10 to 10). 0 is normal speed.
            volume: Volume level (0.0 to 1.0).
        """
        self.voice_id = voice_id
        self.rate = rate
        self.volume = volume
        self._engine = None

    @property
    def engine(self):
        """Lazily initialize the pyttsx3 engine."""
        if self._engine is None:
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._configure_engine()
            except Exception as e:
                raise TTSError(f"Failed to initialize TTS engine: {e}", "local")
        return self._engine

    def _configure_engine(self) -> None:
        """Configure the TTS engine with the specified settings."""
        # Set voice if specified
        if self.voice_id:
            voices = self._engine.getProperty("voices")
            for voice in voices:
                if self.voice_id in voice.id or self.voice_id == voice.name:
                    self._engine.setProperty("voice", voice.id)
                    logger.info(f"Set TTS voice to: {voice.name}")
                    break

        # Adjust rate (pyttsx3 uses words per minute, default ~200)
        current_rate = self._engine.getProperty("rate")
        # Each unit of self.rate adjusts by ~15 WPM
        new_rate = current_rate + (self.rate * 15)
        new_rate = max(50, min(300, new_rate))  # Clamp to reasonable range
        self._engine.setProperty("rate", new_rate)
        logger.debug(f"Set TTS rate to: {new_rate} WPM")

        # Set volume
        self._engine.setProperty("volume", self.volume)
        logger.debug(f"Set TTS volume to: {self.volume}")

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

        Returns:
            Path to the generated audio file.

        Raises:
            TTSError: If synthesis fails.
        """
        logger.info(f"Synthesizing {len(text.split())} words with local TTS")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # pyttsx3 can save directly to file
        # Note: On macOS, it saves as AIFF format, we may need to convert
        temp_path = output_path.with_suffix(".aiff")

        try:
            self.engine.save_to_file(text, str(temp_path))
            self.engine.runAndWait()

            # Check if the file was created
            if not temp_path.exists():
                raise TTSError("Audio file was not created", "local")

            # Convert to WAV using ffmpeg for better compatibility
            self._convert_to_wav(temp_path, output_path)

            # Clean up temporary file
            if temp_path.exists() and temp_path != output_path:
                temp_path.unlink()

            logger.info(f"Successfully saved audio to: {output_path}")
            return output_path

        except Exception as e:
            # Clean up on failure
            if temp_path.exists():
                temp_path.unlink()
            if isinstance(e, TTSError):
                raise
            raise TTSError(f"Failed to synthesize speech: {e}", "local")

    def _convert_to_wav(self, input_path: Path, output_path: Path) -> None:
        """
        Convert audio file to WAV format using ffmpeg.

        Args:
            input_path: Path to the input audio file.
            output_path: Path for the output WAV file.
        """
        import subprocess

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-i", str(input_path),
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "1",  # Mono
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg conversion failed: {result.stderr}")
            raise TTSError(f"Failed to convert audio to WAV: {result.stderr}", "local")

    def list_voices(self) -> list[dict]:
        """
        List all available voices on the system.

        Returns:
            List of dicts with voice information.
        """
        voices = self.engine.getProperty("voices")
        return [
            {
                "id": voice.id,
                "name": voice.name,
                "languages": getattr(voice, "languages", []),
                "gender": getattr(voice, "gender", "unknown"),
            }
            for voice in voices
        ]
