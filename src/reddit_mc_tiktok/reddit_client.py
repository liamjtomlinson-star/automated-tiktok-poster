"""
Reddit API client for fetching story posts.

Uses PRAW (Python Reddit API Wrapper) to interact with the official Reddit API.
Respects Reddit's API rate limits and terms of service.
"""

import logging
from typing import Iterator, Optional

import praw
from praw.models import Submission

from reddit_mc_tiktok.config import Config, RedditConfig
from reddit_mc_tiktok.models import Story


logger = logging.getLogger(__name__)


class RedditClient:
    """
    Client for fetching stories from Reddit.

    Handles authentication and provides methods to fetch posts from
    specified subreddits with various filtering options.
    """

    def __init__(self, config: RedditConfig):
        """
        Initialize the Reddit client with credentials.

        Args:
            config: RedditConfig containing API credentials and settings.
        """
        self.config = config
        self._reddit: Optional[praw.Reddit] = None

    @property
    def reddit(self) -> praw.Reddit:
        """Lazily initialize and return the PRAW Reddit instance."""
        if self._reddit is None:
            self._reddit = praw.Reddit(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                user_agent=self.config.user_agent,
            )
            logger.info("Initialized Reddit API client")
        return self._reddit

    def test_connection(self) -> bool:
        """
        Test the Reddit API connection.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            # Try to access the Reddit instance - this will fail if credentials are invalid
            self.reddit.user.me()
            logger.info("Reddit API connection test successful (authenticated)")
            return True
        except Exception:
            # For read-only access without user auth, try fetching a subreddit
            try:
                subreddit = self.reddit.subreddit("test")
                _ = subreddit.display_name
                logger.info("Reddit API connection test successful (read-only)")
                return True
            except Exception as e:
                logger.error(f"Reddit API connection test failed: {e}")
                return False

    def fetch_posts(
        self,
        subreddit_name: str,
        sort_mode: Optional[str] = None,
        time_filter: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[Story]:
        """
        Fetch posts from a subreddit.

        Args:
            subreddit_name: Name of the subreddit (without r/ prefix).
            sort_mode: How to sort posts (hot, new, top, rising). Defaults to config value.
            time_filter: Time filter for 'top' sort (hour, day, week, month, year, all).
            limit: Maximum number of posts to fetch. Defaults to config value.

        Yields:
            Story objects for each fetched post.
        """
        sort_mode = sort_mode or self.config.sort_mode
        time_filter = time_filter or self.config.time_filter
        limit = limit or self.config.fetch_limit

        logger.info(
            f"Fetching up to {limit} posts from r/{subreddit_name} "
            f"(sort: {sort_mode}, time: {time_filter})"
        )

        subreddit = self.reddit.subreddit(subreddit_name)

        # Get the appropriate listing based on sort mode
        if sort_mode == "hot":
            submissions = subreddit.hot(limit=limit)
        elif sort_mode == "new":
            submissions = subreddit.new(limit=limit)
        elif sort_mode == "rising":
            submissions = subreddit.rising(limit=limit)
        elif sort_mode == "controversial":
            submissions = subreddit.controversial(time_filter=time_filter, limit=limit)
        else:  # default to "top"
            submissions = subreddit.top(time_filter=time_filter, limit=limit)

        count = 0
        for submission in submissions:
            story = self._submission_to_story(submission)
            if story:
                count += 1
                yield story

        logger.info(f"Fetched {count} posts from r/{subreddit_name}")

    def fetch_post_by_id(self, post_id: str) -> Optional[Story]:
        """
        Fetch a specific post by its Reddit ID.

        Args:
            post_id: The Reddit post ID (e.g., "abc123").

        Returns:
            Story object if found and valid, None otherwise.
        """
        logger.info(f"Fetching post with ID: {post_id}")

        try:
            submission = self.reddit.submission(id=post_id)
            # Force load the submission data
            _ = submission.title
            return self._submission_to_story(submission)
        except Exception as e:
            logger.error(f"Failed to fetch post {post_id}: {e}")
            return None

    def fetch_from_multiple_subreddits(
        self,
        subreddit_names: list[str],
        limit_per_subreddit: int = 10,
        sort_mode: Optional[str] = None,
        time_filter: Optional[str] = None,
    ) -> Iterator[Story]:
        """
        Fetch posts from multiple subreddits.

        Args:
            subreddit_names: List of subreddit names to fetch from.
            limit_per_subreddit: Maximum posts to fetch from each subreddit.
            sort_mode: How to sort posts.
            time_filter: Time filter for 'top' sort.

        Yields:
            Story objects from all specified subreddits.
        """
        for subreddit_name in subreddit_names:
            try:
                yield from self.fetch_posts(
                    subreddit_name=subreddit_name,
                    sort_mode=sort_mode,
                    time_filter=time_filter,
                    limit=limit_per_subreddit,
                )
            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                continue

    def _submission_to_story(self, submission: Submission) -> Optional[Story]:
        """
        Convert a PRAW Submission to a Story object.

        Args:
            submission: PRAW Submission object.

        Returns:
            Story object, or None if the submission is not a text post.
        """
        # Skip non-text posts (links, images, videos)
        if not submission.is_self:
            logger.debug(f"Skipping non-text post: {submission.id}")
            return None

        # Skip posts with no text content
        if not submission.selftext or submission.selftext.strip() == "":
            logger.debug(f"Skipping post with no text: {submission.id}")
            return None

        # Get author name safely (deleted authors return None)
        author_name = "[deleted]"
        if submission.author:
            author_name = submission.author.name

        return Story(
            id=submission.id,
            subreddit=submission.subreddit.display_name,
            title=submission.title,
            original_text=submission.selftext,
            url=f"https://reddit.com{submission.permalink}",
            author=author_name,
            score=submission.score,
            num_comments=submission.num_comments,
            is_nsfw=submission.over_18,
            created_utc=submission.created_utc,
        )


def create_reddit_client(config: Config) -> RedditClient:
    """
    Factory function to create a RedditClient from the main config.

    Args:
        config: Main application configuration.

    Returns:
        Configured RedditClient instance.
    """
    return RedditClient(config.reddit)
