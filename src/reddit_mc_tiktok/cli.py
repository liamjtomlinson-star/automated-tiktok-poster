"""
Command-line interface for the Reddit to TikTok video generator.

Provides commands for single video generation, batch processing,
and various utility functions.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from reddit_mc_tiktok.config import load_config, setup_logging, ensure_directories, Config
from reddit_mc_tiktok.models import Story, GeneratedVideo, ProcessingResult
from reddit_mc_tiktok.reddit_client import create_reddit_client
from reddit_mc_tiktok.story_filter import StoryFilter, FilterStats
from reddit_mc_tiktok.story_rewriter import get_rewriter, rewrite_story
from reddit_mc_tiktok.tts import get_tts_provider
from reddit_mc_tiktok.video import VideoBuilder


logger = logging.getLogger(__name__)


def get_output_paths(config: Config, story_id: str) -> dict[str, Path]:
    """Generate output paths for a story."""
    output_dir = config.video.output_directory
    return {
        "audio": output_dir / "audio" / f"story_{story_id}.wav",
        "video": output_dir / "video" / f"story_{story_id}.mp4",
        "script": output_dir / "scripts" / f"story_{story_id}.txt",
        "subtitle": output_dir / "subtitles" / f"story_{story_id}.srt",
    }


def process_single_story(
    story: Story,
    config: Config,
) -> Optional[GeneratedVideo]:
    """
    Process a single story through the full pipeline.

    Steps:
    1. Rewrite the story
    2. Generate TTS audio
    3. Build video with subtitles

    Args:
        story: The Story object to process.
        config: Application configuration.

    Returns:
        GeneratedVideo object if successful, None if failed.
    """
    paths = get_output_paths(config, story.id)

    try:
        # Step 1: Rewrite the story
        logger.info(f"Rewriting story {story.id}...")
        rewriter = get_rewriter(config.rewriter)
        rewritten_text = rewriter.rewrite(
            story.original_text,
            target_word_count=config.rewriter.target_word_count,
        )
        story.rewritten_text = rewritten_text
        story.is_processed = True

        # Save the rewritten script
        paths["script"].parent.mkdir(parents=True, exist_ok=True)
        with open(paths["script"], "w", encoding="utf-8") as f:
            f.write(rewritten_text)
        logger.info(f"Saved script to: {paths['script']}")

        # Step 2: Generate TTS audio
        logger.info(f"Generating audio for story {story.id}...")
        tts = get_tts_provider(config.tts)
        audio_path = tts.synthesize(
            text=story.export_text,  # Always use rewritten text
            output_path=paths["audio"],
        )

        # Step 3: Build video
        logger.info(f"Building video for story {story.id}...")
        video_builder = VideoBuilder(
            video_config=config.video,
            subtitle_config=config.subtitles,
        )
        video_path = video_builder.build_video(
            audio_path=audio_path,
            output_path=paths["video"],
            subtitle_text=story.export_text,  # Always use rewritten text
        )

        # Get video metadata
        duration = video_builder.get_media_duration(video_path)
        file_size = video_path.stat().st_size

        return GeneratedVideo(
            story_id=story.id,
            video_id=story.id,
            video_path=video_path,
            audio_path=audio_path,
            subtitle_path=paths["subtitle"] if paths["subtitle"].exists() else None,
            script_path=paths["script"],
            duration_seconds=duration,
            file_size_bytes=file_size,
            success=True,
        )

    except Exception as e:
        logger.error(f"Failed to process story {story.id}: {e}")
        return GeneratedVideo(
            story_id=story.id,
            video_id=story.id,
            video_path=paths["video"],
            audio_path=paths["audio"],
            success=False,
            error_message=str(e),
        )


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to config.yaml file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: bool):
    """
    Reddit to TikTok Video Generator

    Create TikTok-style videos from Reddit stories with background footage.
    All content is automatically rewritten/paraphrased before export.
    """
    ctx.ensure_object(dict)

    # Load configuration
    try:
        app_config = load_config(config)
        if verbose:
            app_config.log_level = "DEBUG"
        setup_logging(app_config)
        ensure_directories(app_config)
        ctx.obj["config"] = app_config
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)


@cli.command("single")
@click.option(
    "--post-id",
    "-p",
    help="Reddit post ID to process",
)
@click.option(
    "--subreddit",
    "-s",
    help="Subreddit to fetch top post from",
)
@click.pass_context
def generate_single(ctx: click.Context, post_id: Optional[str], subreddit: Optional[str]):
    """
    Generate a single video from a Reddit post.

    Either provide a specific post ID or a subreddit to fetch the top post from.
    """
    config: Config = ctx.obj["config"]

    if not post_id and not subreddit:
        click.echo("Error: Either --post-id or --subreddit is required", err=True)
        sys.exit(1)

    # Create Reddit client
    reddit_client = create_reddit_client(config)

    # Fetch the story
    story: Optional[Story] = None

    if post_id:
        click.echo(f"Fetching post: {post_id}")
        story = reddit_client.fetch_post_by_id(post_id)
    else:
        click.echo(f"Fetching top post from r/{subreddit}")
        stories = list(reddit_client.fetch_posts(subreddit, limit=1))
        if stories:
            story = stories[0]

    if not story:
        click.echo("Error: Could not fetch the story", err=True)
        sys.exit(1)

    # Filter check
    story_filter = StoryFilter(config.filtering)
    passed, reason = story_filter.check_story(story)
    if not passed:
        click.echo(f"Story filtered out: {reason}", err=True)
        click.echo("Use a different story or adjust filter settings.", err=True)
        sys.exit(1)

    click.echo(f"Processing story: {story.title[:50]}...")
    click.echo(f"  - Subreddit: r/{story.subreddit}")
    click.echo(f"  - Length: {story.word_count} words")

    # Process the story
    result = process_single_story(story, config)

    if result and result.success:
        click.echo("\nSuccess!")
        click.echo(f"  - Video: {result.video_path}")
        click.echo(f"  - Audio: {result.audio_path}")
        click.echo(f"  - Script: {result.script_path}")
        click.echo(f"  - Duration: {result.duration_seconds:.1f}s")
    else:
        click.echo(f"\nFailed: {result.error_message if result else 'Unknown error'}", err=True)
        sys.exit(1)


@cli.command("batch")
@click.option(
    "--subreddit",
    "-s",
    help="Subreddit to fetch from (uses config if not specified)",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=5,
    help="Maximum number of videos to generate",
)
@click.option(
    "--sort",
    type=click.Choice(["hot", "new", "top", "rising"]),
    default="top",
    help="Sort mode for fetching posts",
)
@click.option(
    "--time",
    type=click.Choice(["hour", "day", "week", "month", "year", "all"]),
    default="week",
    help="Time filter for 'top' sort",
)
@click.pass_context
def generate_batch(
    ctx: click.Context,
    subreddit: Optional[str],
    limit: int,
    sort: str,
    time: str,
):
    """
    Generate multiple videos from Reddit posts.

    Fetches stories from configured subreddits (or a specific one),
    filters them, and generates videos for each.
    """
    config: Config = ctx.obj["config"]

    # Determine subreddits to use
    subreddits = [subreddit] if subreddit else config.subreddits

    click.echo(f"Batch processing up to {limit} videos")
    click.echo(f"Subreddits: {', '.join(subreddits)}")
    click.echo(f"Sort: {sort}, Time: {time}")
    click.echo()

    # Create Reddit client and filter
    reddit_client = create_reddit_client(config)
    story_filter = StoryFilter(config.filtering)
    filter_stats = FilterStats()

    # Fetch and filter stories
    valid_stories: list[Story] = []
    for sub in subreddits:
        if len(valid_stories) >= limit:
            break

        click.echo(f"Fetching from r/{sub}...")
        stories = reddit_client.fetch_posts(
            sub,
            sort_mode=sort,
            time_filter=time,
            limit=limit * 2,  # Fetch extra to account for filtering
        )

        for story, passed, reason in story_filter.filter_stories(stories):
            filter_stats.record(passed, reason)
            if passed:
                valid_stories.append(story)
                if len(valid_stories) >= limit:
                    break

    click.echo(f"\nFound {len(valid_stories)} valid stories after filtering")
    click.echo(filter_stats.summary())
    click.echo()

    if not valid_stories:
        click.echo("No valid stories found. Try different subreddits or filter settings.", err=True)
        sys.exit(1)

    # Process stories
    result = ProcessingResult(total_attempted=len(valid_stories))

    for i, story in enumerate(valid_stories):
        click.echo(f"[{i + 1}/{len(valid_stories)}] Processing: {story.title[:40]}...")

        video_result = process_single_story(story, config)

        if video_result and video_result.success:
            result.successful.append(video_result)
            click.echo(f"  -> Success: {video_result.video_path.name}")
        else:
            error = video_result.error_message if video_result else "Unknown error"
            result.failed.append((story.id, error))
            click.echo(f"  -> Failed: {error}")

    # Summary
    click.echo()
    click.echo("=" * 50)
    click.echo(result.summary())

    if result.successful:
        click.echo("\nGenerated videos:")
        for video in result.successful:
            click.echo(f"  - {video.video_path}")


@cli.command("test-connection")
@click.pass_context
def test_connection(ctx: click.Context):
    """Test the Reddit API connection."""
    config: Config = ctx.obj["config"]

    click.echo("Testing Reddit API connection...")
    reddit_client = create_reddit_client(config)

    if reddit_client.test_connection():
        click.echo("Connection successful!")
    else:
        click.echo("Connection failed. Check your credentials.", err=True)
        sys.exit(1)


@cli.command("list-subreddits")
@click.pass_context
def list_subreddits(ctx: click.Context):
    """List configured subreddits."""
    config: Config = ctx.obj["config"]

    click.echo("Configured subreddits:")
    for sub in config.subreddits:
        click.echo(f"  - r/{sub}")


@cli.command("rewrite-only")
@click.option(
    "--post-id",
    "-p",
    required=True,
    help="Reddit post ID to rewrite",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for rewritten text",
)
@click.pass_context
def rewrite_only(ctx: click.Context, post_id: str, output: Optional[Path]):
    """
    Rewrite a Reddit story without generating video.

    Useful for testing the rewriting functionality.
    """
    config: Config = ctx.obj["config"]

    click.echo(f"Fetching post: {post_id}")
    reddit_client = create_reddit_client(config)
    story = reddit_client.fetch_post_by_id(post_id)

    if not story:
        click.echo("Error: Could not fetch the story", err=True)
        sys.exit(1)

    click.echo(f"Original ({story.word_count} words):")
    click.echo("-" * 40)
    click.echo(story.original_text[:500] + "..." if len(story.original_text) > 500 else story.original_text)
    click.echo("-" * 40)
    click.echo()

    click.echo("Rewriting...")
    rewriter = get_rewriter(config.rewriter)
    rewritten = rewriter.rewrite(
        story.original_text,
        target_word_count=config.rewriter.target_word_count,
    )

    click.echo(f"\nRewritten ({len(rewritten.split())} words):")
    click.echo("-" * 40)
    click.echo(rewritten)
    click.echo("-" * 40)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(rewritten)
        click.echo(f"\nSaved to: {output}")


@cli.command("list-voices")
@click.pass_context
def list_voices(ctx: click.Context):
    """List available TTS voices."""
    config: Config = ctx.obj["config"]

    click.echo("Available TTS voices:")

    if config.tts.provider == "local":
        from reddit_mc_tiktok.tts import LocalTTS
        tts = LocalTTS()
        voices = tts.list_voices()
        for voice in voices:
            click.echo(f"  - {voice['name']} (ID: {voice['id']})")
    else:
        click.echo("  Voice listing not available for API provider")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
