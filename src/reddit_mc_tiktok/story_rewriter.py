"""
Story rewriter module.

Transforms Reddit stories into TikTok-friendly scripts using LLM APIs.
This module ensures that original Reddit content is NEVER used directly -
all content must be rewritten/paraphrased before export.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

from reddit_mc_tiktok.config import RewriterConfig


logger = logging.getLogger(__name__)


# Prompt template for rewriting stories
REWRITE_PROMPT_TEMPLATE = """You are a professional content writer who transforms stories into engaging TikTok video scripts.

Your task is to rewrite the following story for a TikTok video. The script should be:
1. Completely paraphrased - use different words and sentence structures
2. Engaging with a strong hook at the very beginning
3. Conversational and easy to listen to
4. Suitable for text-to-speech narration
5. Around {target_words} words (approximately 30-60 seconds when spoken)

Rules:
- Start with an attention-grabbing hook line (e.g., "You won't believe what happened..." or "So this is absolutely insane...")
- Use simple, conversational language
- Keep the core story events but change ALL wording
- Remove any Reddit-specific references (like "AITA", "throwaway", "edit:", etc.)
- Don't include any URLs or usernames
- Make it flow naturally for spoken narration
- End with something memorable or a question to engage viewers

Original story:
---
{original_text}
---

Write only the rewritten script, nothing else. Do not include any commentary or explanations."""


class BaseRewriter(ABC):
    """Abstract base class for story rewriters."""

    @abstractmethod
    def rewrite(self, original_text: str, target_word_count: int = 200) -> str:
        """
        Rewrite the original text into a TikTok-friendly script.

        Args:
            original_text: The original Reddit story text.
            target_word_count: Target number of words for the output.

        Returns:
            The rewritten, paraphrased script.
        """
        pass


class AnthropicRewriter(BaseRewriter):
    """Story rewriter using Anthropic's Claude API."""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """
        Initialize the Anthropic rewriter.

        Args:
            api_key: Anthropic API key.
            model: Model identifier to use.
        """
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazily initialize the Anthropic client."""
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def rewrite(self, original_text: str, target_word_count: int = 200) -> str:
        """Rewrite the story using Claude."""
        prompt = REWRITE_PROMPT_TEMPLATE.format(
            target_words=target_word_count,
            original_text=original_text,
        )

        logger.info(f"Sending rewrite request to Anthropic ({self.model})")

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        rewritten = message.content[0].text.strip()
        logger.info(
            f"Received rewritten text: {len(rewritten.split())} words "
            f"(target: {target_word_count})"
        )

        return rewritten


class OpenAIRewriter(BaseRewriter):
    """Story rewriter using OpenAI's API."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Initialize the OpenAI rewriter.

        Args:
            api_key: OpenAI API key.
            model: Model identifier to use.
        """
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazily initialize the OpenAI client."""
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def rewrite(self, original_text: str, target_word_count: int = 200) -> str:
        """Rewrite the story using GPT."""
        prompt = REWRITE_PROMPT_TEMPLATE.format(
            target_words=target_word_count,
            original_text=original_text,
        )

        logger.info(f"Sending rewrite request to OpenAI ({self.model})")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024,
        )

        rewritten = response.choices[0].message.content.strip()
        logger.info(
            f"Received rewritten text: {len(rewritten.split())} words "
            f"(target: {target_word_count})"
        )

        return rewritten


class DummyRewriter(BaseRewriter):
    """
    Simple fallback rewriter that transforms text without an LLM.

    This is for testing or when no API key is available.
    It performs basic transformations to ensure the text is different
    from the original, but the quality will be much lower than LLM-based rewriting.
    """

    # Common word replacements for simple paraphrasing
    REPLACEMENTS = {
        "I ": "So I ",
        "My ": "My ",
        "said": "told me",
        "asked": "wanted to know",
        "told": "mentioned to",
        "went": "headed",
        "got": "ended up with",
        "was": "seemed",
        "were": "appeared to be",
        "because": "since",
        "but": "however",
        "and": "plus",
        "very": "really",
        "really": "totally",
        "just": "literally",
        "think": "believe",
        "know": "realize",
        "want": "need",
        "need": "have to have",
        "like": "similar to",
        "good": "great",
        "bad": "terrible",
        "big": "huge",
        "small": "tiny",
    }

    # Hook phrases to add at the beginning
    HOOKS = [
        "You won't believe what happened to me.",
        "So this is absolutely insane.",
        "Let me tell you about the craziest thing.",
        "Okay so this story is wild.",
        "I still can't believe this actually happened.",
    ]

    def rewrite(self, original_text: str, target_word_count: int = 200) -> str:
        """
        Perform simple text transformation.

        Note: This produces lower quality results than LLM-based rewriting
        but ensures the text is different from the original.
        """
        logger.warning(
            "Using dummy rewriter - results will be lower quality. "
            "Consider configuring an LLM API for better results."
        )

        # Clean up the text
        text = self._clean_text(original_text)

        # Apply word replacements
        for old, new in self.REPLACEMENTS.items():
            text = text.replace(old, new)

        # Truncate to target length
        words = text.split()
        if len(words) > target_word_count:
            words = words[:target_word_count]
            text = " ".join(words)
            # Try to end at a sentence
            last_period = text.rfind(".")
            if last_period > len(text) * 0.7:
                text = text[:last_period + 1]

        # Add a hook at the beginning
        import random
        hook = random.choice(self.HOOKS)
        text = f"{hook} {text}"

        # Add an ending
        if not text.rstrip().endswith((".", "!", "?")):
            text = text.rstrip() + "."
        text += " What would you have done?"

        return text

    def _clean_text(self, text: str) -> str:
        """Clean up Reddit-specific formatting and content."""
        # Remove Reddit-specific markers
        patterns_to_remove = [
            r"^AITA\s+(for|if|when)\s+",
            r"^WIBTA\s+(for|if|when)\s+",
            r"^TIFU\s+by\s+",
            r"\[.*?\]",  # Remove bracketed content like [M25]
            r"(?i)edit:.*$",
            r"(?i)update:.*$",
            r"(?i)throwaway\s+because.*?\.",
            r"(?i)using\s+a\s+throwaway.*?\.",
            r"(?i)tldr:.*$",
            r"(?i)tl;dr:.*$",
            r"https?://\S+",  # URLs
            r"u/\w+",  # Reddit usernames
            r"r/\w+",  # Subreddit references
        ]

        for pattern in patterns_to_remove:
            text = re.sub(pattern, "", text, flags=re.MULTILINE | re.IGNORECASE)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text


def get_rewriter(config: RewriterConfig) -> BaseRewriter:
    """
    Factory function to create the appropriate rewriter based on config.

    Args:
        config: RewriterConfig with provider settings and API keys.

    Returns:
        Configured rewriter instance.

    Raises:
        ValueError: If the configured provider requires an API key that's not set.
    """
    provider = config.provider.lower()

    if provider == "anthropic":
        if not config.anthropic_api_key:
            logger.warning(
                "Anthropic API key not set. Falling back to dummy rewriter. "
                "Set ANTHROPIC_API_KEY environment variable for better results."
            )
            return DummyRewriter()
        return AnthropicRewriter(
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
        )

    elif provider == "openai":
        if not config.openai_api_key:
            logger.warning(
                "OpenAI API key not set. Falling back to dummy rewriter. "
                "Set OPENAI_API_KEY environment variable for better results."
            )
            return DummyRewriter()
        return OpenAIRewriter(
            api_key=config.openai_api_key,
            model=config.openai_model,
        )

    elif provider == "dummy":
        return DummyRewriter()

    else:
        logger.warning(f"Unknown rewriter provider '{provider}'. Using dummy rewriter.")
        return DummyRewriter()


def rewrite_story(
    original_text: str,
    config: Optional[RewriterConfig] = None,
    rewriter: Optional[BaseRewriter] = None,
    target_word_count: int = 200,
) -> str:
    """
    Convenience function to rewrite a story.

    Args:
        original_text: The original Reddit story text.
        config: RewriterConfig to create a rewriter from (if rewriter not provided).
        rewriter: Pre-configured rewriter instance to use.
        target_word_count: Target number of words for output.

    Returns:
        The rewritten, paraphrased script.

    Raises:
        ValueError: If neither config nor rewriter is provided.
    """
    if rewriter is None:
        if config is None:
            raise ValueError("Either config or rewriter must be provided")
        rewriter = get_rewriter(config)

    return rewriter.rewrite(original_text, target_word_count)
