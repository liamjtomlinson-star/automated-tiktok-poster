# Reddit to TikTok Video Generator

A command-line tool that automates creating TikTok-style vertical videos from Reddit stories with Minecraft parkour footage in the background.

## Features

- **Reddit Integration**: Fetches story posts from configurable subreddits using the official Reddit API
- **Content Filtering**: Filters posts by length, NSFW status, and banned keywords
- **AI-Powered Rewriting**: Transforms stories into engaging, TikTok-friendly scripts using LLM APIs
- **Text-to-Speech**: Converts scripts to voiceover audio with pluggable TTS providers
- **Video Generation**: Creates vertical 9:16 (1080x1920) videos with background footage
- **Auto-Subtitles**: Generates and burns readable captions onto videos
- **Batch Processing**: Process multiple stories into videos in one command

## Important Notes

### Content Compliance

This tool is designed to create **transformative content** only:

- **Original Reddit text is NEVER used directly** - all content is rewritten/paraphrased before export
- The tool fetches stories, immediately rewrites them, and only exports the paraphrased version
- You must provide your own background video footage (recorded by you or royalty-free/public domain)
- No copyrighted materials are included in this repository

### Your Responsibilities

- Follow [Reddit's API Terms of Service](https://www.reddit.com/wiki/api-terms)
- Ensure your use of Reddit-sourced ideas is compliant and transformative
- Only use background footage you have rights to use
- Follow TikTok's community guidelines when posting

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.10+
- ffmpeg
- Reddit API credentials
- (Optional) LLM API key (Anthropic/OpenAI) for AI-powered rewriting
- (Optional) TTS API key for cloud-based text-to-speech

## Installation

### 1. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python and ffmpeg

```bash
# Install Python 3
brew install python@3.11

# Install ffmpeg (required for video processing)
brew install ffmpeg
```

### 3. Clone and Set Up the Project

```bash
# Clone the repository
git clone https://github.com/yourusername/reddit-mc-tiktok.git
cd reddit-mc-tiktok

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Reddit API Credentials

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in the details:
   - Name: Your app name
   - App type: Select "script"
   - Description: Optional
   - Redirect URI: `http://localhost:8080`
4. Note your `client_id` (under the app name) and `client_secret`

### 5. Set Up Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Reddit API Credentials
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=RedditMCTikTok/1.0 by YourUsername

# LLM API (choose one)
ANTHROPIC_API_KEY=your_anthropic_key_here
# OPENAI_API_KEY=your_openai_key_here

# TTS Provider: "local" or "api"
TTS_PROVIDER=local

# External TTS API (if using api provider)
# TTS_API_KEY=your_tts_api_key_here
# TTS_API_URL=https://api.example.com/tts
```

### 6. Configure the Tool

Edit `config.yaml` to customize settings:

```yaml
# Subreddits to fetch from
subreddits:
  - AmItheAsshole
  - TrueOffMyChest
  - tifu
  - relationship_advice

# Story filtering
min_story_length: 500
max_story_length: 5000
allow_nsfw: false
banned_keywords:
  - spam
  - advertisement

# Reddit fetch settings
sort_mode: top  # hot, new, top, rising
time_filter: week  # hour, day, week, month, year, all

# Video settings
background_video_path: assets/minecraft_parkour.mp4
output_directory: output
video_width: 1080
video_height: 1920

# TTS settings
tts_provider: local  # local or api
speech_rate: 150  # words per minute

# Rewriter settings
rewriter_provider: anthropic  # anthropic, openai, or dummy
target_word_count: 200
```

### 7. Add Your Background Video

Place your Minecraft parkour video (or any background footage you have rights to use) at:

```
assets/minecraft_parkour.mp4
```

The video should be:
- Vertical format (9:16 aspect ratio) preferred, or will be cropped
- At least 60 seconds long (will be looped if shorter than audio)
- Your own recording or royalty-free/public domain footage

## Usage

### Generate a Single Video

Process one Reddit post by ID:

```bash
# Activate virtual environment first
source venv/bin/activate

# Generate from a specific post
python -m reddit_mc_tiktok single --post-id abc123

# Or fetch the top post from a subreddit
python -m reddit_mc_tiktok single --subreddit AmItheAsshole
```

### Batch Generate Videos

Process multiple posts at once:

```bash
# Generate 5 videos from configured subreddits
python -m reddit_mc_tiktok batch --limit 5

# Generate from a specific subreddit
python -m reddit_mc_tiktok batch --subreddit tifu --limit 10

# Use specific sort mode and time filter
python -m reddit_mc_tiktok batch --subreddit AmItheAsshole --sort top --time week --limit 5
```

### Using Shell Scripts

Convenience scripts are provided in the `scripts/` directory:

```bash
# Run setup (creates venv, installs deps)
./scripts/setup.sh

# Generate a single video
./scripts/run_single.sh

# Batch generate videos
./scripts/run_batch.sh
```

### Additional Commands

```bash
# Show help
python -m reddit_mc_tiktok --help

# Test Reddit connection
python -m reddit_mc_tiktok test-connection

# List available subreddits from config
python -m reddit_mc_tiktok list-subreddits

# Rewrite a story without generating video (for testing)
python -m reddit_mc_tiktok rewrite-only --post-id abc123
```

## Output

Generated files are saved to the `output/` directory:

```
output/
├── audio/
│   ├── story_001.wav
│   ├── story_002.wav
│   └── ...
├── video/
│   ├── story_001.mp4
│   ├── story_002.mp4
│   └── ...
├── scripts/
│   ├── story_001.txt  (rewritten script)
│   ├── story_002.txt
│   └── ...
└── subtitles/
    ├── story_001.srt
    ├── story_002.srt
    └── ...
```

## Project Structure

```
reddit-mc-tiktok/
├── README.md
├── requirements.txt
├── pyproject.toml
├── config.yaml
├── .env.example
├── .gitignore
├── src/
│   └── reddit_mc_tiktok/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── reddit_client.py
│       ├── story_filter.py
│       ├── story_rewriter.py
│       ├── models.py
│       ├── tts/
│       │   ├── __init__.py
│       │   ├── base_tts.py
│       │   ├── local_tts.py
│       │   └── api_tts_placeholder.py
│       └── video/
│           ├── __init__.py
│           ├── video_builder.py
│           └── subtitles.py
├── scripts/
│   ├── setup.sh
│   ├── run_single.sh
│   └── run_batch.sh
├── assets/
│   └── .gitkeep
└── output/
    └── .gitkeep
```

## Customization

### Adding a New TTS Provider

1. Create a new class in `src/reddit_mc_tiktok/tts/` that extends `BaseTTS`
2. Implement the `synthesize()` method
3. Register it in `src/reddit_mc_tiktok/tts/__init__.py`

### Adding a New Rewriter Provider

1. Create a new function in `story_rewriter.py` following the existing pattern
2. Add a new case in the `get_rewriter()` factory function

### Customizing Subtitles

Edit the subtitle settings in `src/reddit_mc_tiktok/video/subtitles.py`:
- Font size
- Position
- Colors
- Timing

## Troubleshooting

### ffmpeg not found

```bash
brew install ffmpeg
```

### Reddit API authentication errors

- Verify your credentials in `.env`
- Make sure your Reddit app is set to "script" type
- Check that your user agent follows Reddit's guidelines

### TTS errors on macOS

For local TTS, ensure you have the required system libraries:

```bash
pip install pyttsx3
```

### Video generation fails

- Ensure your background video exists at the configured path
- Check that ffmpeg is installed and accessible
- Verify you have write permissions to the output directory

## Legal / Copyright Considerations

### Reddit Content

- This tool transforms Reddit content into paraphrased scripts
- Original Reddit text is never exported or published
- Users must comply with [Reddit's API Terms](https://www.reddit.com/wiki/api-terms)
- Consider the transformative nature of your content

### Background Footage

- You must provide your own background video
- Use only footage you have recorded yourself, or
- Use royalty-free / public domain footage with appropriate licenses
- Do NOT use copyrighted gameplay footage without permission

### TikTok Publishing

- Follow TikTok's Community Guidelines
- Respect content attribution requirements
- Be aware of monetization policies

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is provided for educational and personal use. Users are solely responsible for ensuring their use of this tool complies with all applicable laws, terms of service, and platform guidelines. The authors are not responsible for any misuse of this tool or any content created with it.
