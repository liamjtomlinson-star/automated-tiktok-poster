"""
Video builder module.

Combines background video, audio, and subtitles into final TikTok-style videos.
Uses ffmpeg for all video processing operations.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

from reddit_mc_tiktok.config import VideoConfig, SubtitleConfig
from reddit_mc_tiktok.video.subtitles import SubtitleGenerator


logger = logging.getLogger(__name__)


class VideoBuilder:
    """
    Builds TikTok-style vertical videos.

    Combines background footage with voiceover audio and burnt-in subtitles
    to create final video output in 9:16 vertical format (1080x1920).
    """

    def __init__(
        self,
        video_config: VideoConfig,
        subtitle_config: Optional[SubtitleConfig] = None,
    ):
        """
        Initialize the video builder.

        Args:
            video_config: VideoConfig with video settings.
            subtitle_config: SubtitleConfig for subtitle generation. Optional.
        """
        self.video_config = video_config
        self.subtitle_config = subtitle_config
        self._subtitle_generator: Optional[SubtitleGenerator] = None

    @property
    def subtitle_generator(self) -> Optional[SubtitleGenerator]:
        """Lazily initialize subtitle generator if config is provided."""
        if self._subtitle_generator is None and self.subtitle_config:
            self._subtitle_generator = SubtitleGenerator(self.subtitle_config)
        return self._subtitle_generator

    def check_ffmpeg(self) -> bool:
        """
        Check if ffmpeg is installed and accessible.

        Returns:
            True if ffmpeg is available, False otherwise.
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                logger.debug("ffmpeg is available")
                return True
            return False
        except FileNotFoundError:
            logger.error(
                "ffmpeg not found. Please install it with: brew install ffmpeg"
            )
            return False

    def get_media_duration(self, file_path: Path) -> float:
        """
        Get the duration of a media file in seconds.

        Args:
            file_path: Path to audio or video file.

        Returns:
            Duration in seconds.

        Raises:
            RuntimeError: If duration cannot be determined.
        """
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get media duration: {result.stderr}")

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def get_video_dimensions(self, file_path: Path) -> tuple[int, int]:
        """
        Get the dimensions of a video file.

        Args:
            file_path: Path to video file.

        Returns:
            Tuple of (width, height).
        """
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-select_streams", "v:0",
                str(file_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get video dimensions: {result.stderr}")

        data = json.loads(result.stdout)
        stream = data["streams"][0]
        return int(stream["width"]), int(stream["height"])

    def build_video(
        self,
        audio_path: Path,
        output_path: Path,
        subtitle_text: Optional[str] = None,
        background_video_path: Optional[Path] = None,
    ) -> Path:
        """
        Build the final video combining all elements.

        Args:
            audio_path: Path to the voiceover audio file.
            output_path: Path for the final video output.
            subtitle_text: Text content for generating subtitles.
            background_video_path: Custom background video. Uses config default if not provided.

        Returns:
            Path to the generated video file.

        Raises:
            FileNotFoundError: If required files don't exist.
            RuntimeError: If video generation fails.
        """
        if not self.check_ffmpeg():
            raise RuntimeError("ffmpeg is not installed")

        # Determine background video path
        bg_video = background_video_path or self.video_config.background_video_path
        if not bg_video.exists():
            raise FileNotFoundError(
                f"Background video not found: {bg_video}\n"
                "Please provide a background video file at the configured path."
            )

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get audio duration
        audio_duration = self.get_media_duration(audio_path)
        logger.info(f"Audio duration: {audio_duration:.2f} seconds")

        # Generate subtitles if text is provided
        srt_path: Optional[Path] = None
        if subtitle_text and self.subtitle_generator and self.subtitle_config.enabled:
            srt_path = output_path.with_suffix(".srt")
            self.subtitle_generator.generate_srt_file(
                text=subtitle_text,
                audio_duration=audio_duration,
                output_path=srt_path,
            )

        # Build the ffmpeg command
        ffmpeg_cmd = self._build_ffmpeg_command(
            background_video=bg_video,
            audio_path=audio_path,
            output_path=output_path,
            duration=audio_duration,
            srt_path=srt_path,
        )

        logger.info(f"Running ffmpeg to generate video...")
        logger.debug(f"Command: {' '.join(ffmpeg_cmd)}")

        # Execute ffmpeg
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            raise RuntimeError(f"Video generation failed: {result.stderr}")

        if not output_path.exists():
            raise RuntimeError("Video file was not created")

        logger.info(f"Successfully generated video: {output_path}")
        return output_path

    def _build_ffmpeg_command(
        self,
        background_video: Path,
        audio_path: Path,
        output_path: Path,
        duration: float,
        srt_path: Optional[Path] = None,
    ) -> list[str]:
        """
        Build the ffmpeg command for video generation.

        Args:
            background_video: Path to background video.
            audio_path: Path to audio file.
            output_path: Path for output video.
            duration: Target video duration in seconds.
            srt_path: Path to SRT subtitle file (optional).

        Returns:
            ffmpeg command as a list of arguments.
        """
        target_width = self.video_config.width
        target_height = self.video_config.height

        # Build the filter complex
        filters = []

        # Step 1: Loop/trim the background video to match audio duration
        # Using -stream_loop for looping and -t for trimming
        # Scale and crop to target dimensions (9:16 vertical)
        scale_crop_filter = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height}"
        )
        filters.append(scale_crop_filter)

        # Step 2: Add subtitles if available
        if srt_path and srt_path.exists():
            subtitle_filter = self.subtitle_generator.get_ffmpeg_subtitle_filter(srt_path)
            filters.append(subtitle_filter)

        # Combine filters
        filter_complex = ",".join(filters)

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-stream_loop", "-1",  # Loop background video indefinitely
            "-i", str(background_video),  # Input 0: background video
            "-i", str(audio_path),  # Input 1: audio
            "-t", str(duration),  # Output duration (matches audio)
            "-filter_complex", filter_complex,
            "-map", "0:v",  # Use video from input 0
            "-map", "1:a",  # Use audio from input 1
            "-c:v", self.video_config.video_codec,
            "-preset", "medium",
            "-crf", str(self.video_config.crf),
            "-c:a", self.video_config.audio_codec,
            "-b:a", "192k",
            "-r", str(self.video_config.fps),
            "-pix_fmt", "yuv420p",  # Compatibility
            "-shortest",  # End when shortest input ends
            str(output_path),
        ]

        return cmd

    def build_video_batch(
        self,
        items: list[tuple[Path, Path, Optional[str]]],
    ) -> list[Path]:
        """
        Build multiple videos in sequence.

        Args:
            items: List of tuples (audio_path, output_path, subtitle_text).

        Returns:
            List of successfully generated video paths.
        """
        successful = []

        for i, (audio_path, output_path, subtitle_text) in enumerate(items):
            logger.info(f"Building video {i + 1}/{len(items)}: {output_path.name}")
            try:
                result = self.build_video(
                    audio_path=audio_path,
                    output_path=output_path,
                    subtitle_text=subtitle_text,
                )
                successful.append(result)
            except Exception as e:
                logger.error(f"Failed to build video {output_path.name}: {e}")
                continue

        logger.info(f"Successfully built {len(successful)}/{len(items)} videos")
        return successful


def create_video_builder(
    video_config: VideoConfig,
    subtitle_config: Optional[SubtitleConfig] = None,
) -> VideoBuilder:
    """Factory function to create a VideoBuilder."""
    return VideoBuilder(video_config, subtitle_config)
