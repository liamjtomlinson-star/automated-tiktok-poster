"""
Story filtering module.

Filters Reddit stories based on configurable criteria like length,
NSFW status, and banned keywords.
"""

import logging
import re
from typing import Iterator, Optional

from reddit_mc_tiktok.config import FilteringConfig
from reddit_mc_tiktok.models import Story


logger = logging.getLogger(__name__)


class StoryFilter:
    """
    Filters stories based on configured criteria.

    Provides methods to check individual stories or filter collections
    of stories based on length, NSFW status, and content keywords.
    """

    def __init__(self, config: FilteringConfig):
        """
        Initialize the story filter with configuration.

        Args:
            config: FilteringConfig containing filter criteria.
        """
        self.config = config
        self._banned_patterns = self._compile_banned_patterns()

    def _compile_banned_patterns(self) -> list[re.Pattern]:
        """Compile banned keywords into regex patterns for efficient matching."""
        patterns = []
        for keyword in self.config.banned_keywords:
            # Escape special regex characters and create case-insensitive pattern
            escaped = re.escape(keyword)
            pattern = re.compile(escaped, re.IGNORECASE)
            patterns.append(pattern)
        return patterns

    def check_story(self, story: Story) -> tuple[bool, Optional[str]]:
        """
        Check if a story passes all filter criteria.

        Args:
            story: The Story object to check.

        Returns:
            Tuple of (passes_filter, rejection_reason).
            If passes_filter is True, rejection_reason will be None.
        """
        # Check NSFW
        if story.is_nsfw and not self.config.allow_nsfw:
            return False, "NSFW content not allowed"

        # Check minimum length
        if story.char_count < self.config.min_story_length:
            return False, f"Too short ({story.char_count} chars < {self.config.min_story_length})"

        # Check maximum length
        if story.char_count > self.config.max_story_length:
            return False, f"Too long ({story.char_count} chars > {self.config.max_story_length})"

        # Check for banned keywords in title and text
        combined_text = f"{story.title} {story.original_text}"
        for pattern in self._banned_patterns:
            if pattern.search(combined_text):
                return False, f"Contains banned keyword: {pattern.pattern}"

        # Check for deleted/removed content
        if story.original_text.strip().lower() in ["[removed]", "[deleted]"]:
            return False, "Content has been removed or deleted"

        return True, None

    def filter_stories(
        self,
        stories: Iterator[Story],
        max_results: Optional[int] = None,
    ) -> Iterator[tuple[Story, bool, Optional[str]]]:
        """
        Filter a collection of stories.

        Args:
            stories: Iterator of Story objects to filter.
            max_results: Maximum number of passing stories to yield.

        Yields:
            Tuples of (story, passed, reason) for each story.
        """
        passed_count = 0

        for story in stories:
            passed, reason = self.check_story(story)

            if passed:
                passed_count += 1
                logger.debug(f"Story {story.id} passed filter")
            else:
                logger.debug(f"Story {story.id} filtered out: {reason}")

            yield story, passed, reason

            # Stop if we've reached max results
            if max_results and passed_count >= max_results:
                break

    def get_valid_stories(
        self,
        stories: Iterator[Story],
        max_results: Optional[int] = None,
    ) -> Iterator[Story]:
        """
        Get only stories that pass all filters.

        Args:
            stories: Iterator of Story objects to filter.
            max_results: Maximum number of stories to yield.

        Yields:
            Story objects that pass all filter criteria.
        """
        for story, passed, _ in self.filter_stories(stories, max_results):
            if passed:
                yield story


class FilterStats:
    """Tracks statistics about filtering operations."""

    def __init__(self):
        self.total_processed = 0
        self.passed = 0
        self.rejected_nsfw = 0
        self.rejected_too_short = 0
        self.rejected_too_long = 0
        self.rejected_banned_keyword = 0
        self.rejected_removed = 0
        self.rejected_other = 0

    def record(self, passed: bool, reason: Optional[str]) -> None:
        """Record the result of a filter check."""
        self.total_processed += 1

        if passed:
            self.passed += 1
        elif reason:
            if "NSFW" in reason:
                self.rejected_nsfw += 1
            elif "Too short" in reason:
                self.rejected_too_short += 1
            elif "Too long" in reason:
                self.rejected_too_long += 1
            elif "banned keyword" in reason.lower():
                self.rejected_banned_keyword += 1
            elif "removed" in reason.lower() or "deleted" in reason.lower():
                self.rejected_removed += 1
            else:
                self.rejected_other += 1
        else:
            self.rejected_other += 1

    def summary(self) -> str:
        """Return a summary of filter statistics."""
        if self.total_processed == 0:
            return "No stories processed"

        pass_rate = (self.passed / self.total_processed) * 100
        return (
            f"Filter stats: {self.passed}/{self.total_processed} passed ({pass_rate:.1f}%)\n"
            f"  - NSFW rejected: {self.rejected_nsfw}\n"
            f"  - Too short: {self.rejected_too_short}\n"
            f"  - Too long: {self.rejected_too_long}\n"
            f"  - Banned keywords: {self.rejected_banned_keyword}\n"
            f"  - Removed/deleted: {self.rejected_removed}\n"
            f"  - Other: {self.rejected_other}"
        )
