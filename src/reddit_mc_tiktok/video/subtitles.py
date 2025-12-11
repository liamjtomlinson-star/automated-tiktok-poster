"""
Subtitle generation module.

Creates SRT subtitle files and provides subtitle timing based on text content.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from reddit_mc_tiktok.config import SubtitleConfig


logger = logging.getLogger(__name__)


@dataclass
class Subtitle:
    """Represents a single subtitle entry."""

    index: int
    start_time: float  # seconds
    end_time: float  # seconds
    text: str

    def to_srt_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def to_srt_entry(self) -> str:
        """Convert to SRT format entry."""
        start = self.to_srt_timestamp(self.start_time)
        end = self.to_srt_timestamp(self.end_time)
        return f"{self.index}\n{start} --> {end}\n{self.text}\n"


class SubtitleGenerator:
    """
    Generates subtitles from text content.

    Creates timed subtitle segments based on text length and estimated
    reading speed, outputting in SRT format.
    """

    def __init__(self, config: SubtitleConfig):
        """
        Initialize the subtitle generator.

        Args:
            config: SubtitleConfig with subtitle settings.
        """
        self.config = config

    def generate_subtitles(
        self,
        text: str,
        audio_duration: float,
        words_per_segment: Optional[int] = None,
    ) -> list[Subtitle]:
        """
        Generate subtitles from text synchronized to audio duration.

        Args:
            text: The text content to create subtitles for.
            audio_duration: Total audio duration in seconds.
            words_per_segment: Number of words per subtitle. Defaults to config.

        Returns:
            List of Subtitle objects.
        """
        words_per_segment = words_per_segment or self.config.words_per_segment

        # Clean and split the text into words
        words = self._clean_text(text).split()
        total_words = len(words)

        if total_words == 0:
            return []

        # Calculate timing
        time_per_word = audio_duration / total_words

        subtitles = []
        index = 1
        word_index = 0

        while word_index < total_words:
            # Get the next segment of words
            segment_words = words[word_index:word_index + words_per_segment]
            segment_text = " ".join(segment_words)

            # Wrap long lines
            segment_text = self._wrap_text(segment_text)

            # Calculate timing for this segment
            start_time = word_index * time_per_word
            end_time = min(
                (word_index + len(segment_words)) * time_per_word,
                audio_duration
            )

            # Add a small gap between subtitles for readability
            if index > 1:
                start_time += 0.05

            subtitle = Subtitle(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=segment_text,
            )
            subtitles.append(subtitle)

            index += 1
            word_index += len(segment_words)

        logger.info(f"Generated {len(subtitles)} subtitle segments")
        return subtitles

    def generate_srt_file(
        self,
        text: str,
        audio_duration: float,
        output_path: Path,
        words_per_segment: Optional[int] = None,
    ) -> Path:
        """
        Generate an SRT subtitle file.

        Args:
            text: The text content to create subtitles for.
            audio_duration: Total audio duration in seconds.
            output_path: Path for the output SRT file.
            words_per_segment: Number of words per subtitle.

        Returns:
            Path to the generated SRT file.
        """
        subtitles = self.generate_subtitles(text, audio_duration, words_per_segment)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write SRT file
        with open(output_path, "w", encoding="utf-8") as f:
            for subtitle in subtitles:
                f.write(subtitle.to_srt_entry())
                f.write("\n")

        logger.info(f"Saved SRT file to: {output_path}")
        return output_path

    def _clean_text(self, text: str) -> str:
        """Clean text for subtitle display."""
        # Remove multiple spaces
        text = re.sub(r"\s+", " ", text)
        # Remove any remaining newlines
        text = text.replace("\n", " ")
        return text.strip()

    def _wrap_text(self, text: str) -> str:
        """
        Wrap text to fit within max_chars_per_line.

        Args:
            text: The text to wrap.

        Returns:
            Text with line breaks inserted.
        """
        max_chars = self.config.max_chars_per_line
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)
            # +1 for the space before the word
            if current_length + word_length + (1 if current_line else 0) <= max_chars:
                current_line.append(word)
                current_length += word_length + (1 if len(current_line) > 1 else 0)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_length

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)

    def get_ffmpeg_subtitle_filter(
        self,
        srt_path: Path,
        force_style: bool = True,
    ) -> str:
        """
        Generate ffmpeg subtitle filter string.

        This creates the filter for burning subtitles into video.

        Args:
            srt_path: Path to the SRT file.
            force_style: Whether to apply custom styling.

        Returns:
            ffmpeg filter string for subtitles.
        """
        # Escape special characters in path for ffmpeg
        escaped_path = str(srt_path).replace(":", "\\:").replace("'", "\\'")

        if force_style:
            # Build ASS style string
            style = (
                f"FontName={self.config.font_name},"
                f"FontSize={self.config.font_size},"
                f"PrimaryColour=&H00{self._reverse_hex(self.config.font_color)},"
                f"OutlineColour=&H00{self._reverse_hex(self.config.outline_color)},"
                f"Outline={self.config.outline_width},"
                f"Shadow=1,"
                f"Alignment=2,"  # Bottom center
                f"MarginV={self.config.margin_bottom}"
            )
            return f"subtitles='{escaped_path}':force_style='{style}'"
        else:
            return f"subtitles='{escaped_path}'"

    def _reverse_hex(self, hex_color: str) -> str:
        """
        Reverse hex color from RGB to BGR for ASS format.

        ASS format uses BBGGRR instead of RRGGBB.
        """
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"{b}{g}{r}"
        return hex_color


def create_subtitle_generator(config: SubtitleConfig) -> SubtitleGenerator:
    """Factory function to create a SubtitleGenerator."""
    return SubtitleGenerator(config)
