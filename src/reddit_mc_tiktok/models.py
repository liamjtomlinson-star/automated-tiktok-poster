"""
Data models for the Reddit to TikTok video generator.

This module defines the core data structures used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Story:
    """
    Represents a Reddit story post.

    Contains both the original fetched data and any processed/rewritten content.
    The original_text is kept for reference but should NEVER be exported directly.
    Only the rewritten_text should be used for video generation.
    """

    # Unique Reddit post identifier
    id: str

    # Subreddit the story came from (without r/ prefix)
    subreddit: str

    # Post title
    title: str

    # Original story text (kept internally, never exported)
    original_text: str

    # Full URL to the Reddit post
    url: str

    # Post author username
    author: str

    # Post score (upvotes - downvotes)
    score: int

    # Number of comments
    num_comments: int

    # Whether the post is marked NSFW
    is_nsfw: bool

    # Unix timestamp when post was created
    created_utc: float

    # Rewritten/paraphrased text for TikTok (this is what gets exported)
    rewritten_text: Optional[str] = None

    # Whether this story has been processed
    is_processed: bool = False

    # Timestamp when story was fetched
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def word_count(self) -> int:
        """Return word count of the original text."""
        return len(self.original_text.split())

    @property
    def char_count(self) -> int:
        """Return character count of the original text."""
        return len(self.original_text)

    @property
    def rewritten_word_count(self) -> Optional[int]:
        """Return word count of the rewritten text, if available."""
        if self.rewritten_text:
            return len(self.rewritten_text.split())
        return None

    @property
    def export_text(self) -> str:
        """
        Return the text that should be used for export/video generation.

        IMPORTANT: This always returns the rewritten text, never the original.
        Raises an error if the story hasn't been rewritten yet.
        """
        if not self.rewritten_text:
            raise ValueError(
                f"Story {self.id} has not been rewritten yet. "
                "Original Reddit content cannot be exported directly."
            )
        return self.rewritten_text

    def __str__(self) -> str:
        status = "processed" if self.is_processed else "raw"
        return f"Story({self.id}, r/{self.subreddit}, {self.word_count} words, {status})"


@dataclass
class GeneratedVideo:
    """
    Represents a generated TikTok video and its associated files.
    """

    # Reference to the source story
    story_id: str

    # Unique identifier for this video
    video_id: str

    # Path to the final video file
    video_path: Path

    # Path to the audio file
    audio_path: Path

    # Path to the subtitle file (SRT)
    subtitle_path: Optional[Path] = None

    # Path to the saved script text
    script_path: Optional[Path] = None

    # Video duration in seconds
    duration_seconds: float = 0.0

    # Video file size in bytes
    file_size_bytes: int = 0

    # Timestamp when video was generated
    generated_at: datetime = field(default_factory=datetime.now)

    # Whether generation was successful
    success: bool = True

    # Error message if generation failed
    error_message: Optional[str] = None

    def __str__(self) -> str:
        status = "success" if self.success else "failed"
        return f"GeneratedVideo({self.video_id}, {self.duration_seconds:.1f}s, {status})"


@dataclass
class ProcessingResult:
    """
    Result of processing a batch of stories.
    """

    # Total stories attempted
    total_attempted: int

    # Successfully generated videos
    successful: list[GeneratedVideo] = field(default_factory=list)

    # Failed generations with error info
    failed: list[tuple[str, str]] = field(default_factory=list)

    # Stories that were filtered out
    filtered_out: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        """Number of successfully generated videos."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed generations."""
        return len(self.failed)

    @property
    def filtered_count(self) -> int:
        """Number of stories filtered out."""
        return len(self.filtered_out)

    def summary(self) -> str:
        """Return a summary of the processing results."""
        return (
            f"Processing complete: {self.success_count}/{self.total_attempted} successful, "
            f"{self.failure_count} failed, {self.filtered_count} filtered out"
        )
