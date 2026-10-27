<div align="center">
  <img src="assets/banner.gif" alt="Neo AI Bot animated banner" width="100%">
  <h1>Neo-AI-Bot</h1>
  <h3>Multi-mode AI Telegram Bot</h3>
  <p>Chat · Coding · Image · Video · Admin CRM</p>
  <a href="https://t.me/NeoTenet"><img src="https://img.shields.io/badge/Telegram-NeoTenet-229ED9?style=for-the-badge&logo=telegram&logoColor=white&labelColor=09152f" alt="Telegram"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=09152f" alt="Python">
  <img src="https://img.shields.io/badge/Storage-Upstash%20Redis-00C98D?style=for-the-badge&logo=redis&logoColor=white&labelColor=09152f" alt="Upstash Redis">
  <br><br>
  <a href="README.md">🇮🇷 راهنمای فارسی</a> · <a href="https://github.com/NeoTenet/Neo-Ai-Bot-Python/issues">Report an issue</a>
</div>

<img src="assets/divider.gif" alt="animated divider" width="100%">

## Overview

Neo-AI-Bot is a Python Telegram bot with separate modes for chat, coding, image generation, and video generation. It uses Upstash Redis REST for persisted settings, user records, and chat-history metadata.

## Main features

<img src="assets/features.gif" alt="Neo AI Bot feature cards" width="100%">

- Four user-facing modes: chat, coding, image, and video.
- Separate model registries for chat, programming, image, and video.
- Model selection updates the welcome banner with the active mode and model name.
- Long code blocks can be delivered as downloadable files for supported languages.
- Image/video API flows can poll asynchronous jobs when supported by the provider's API format.
- Video model entries can include a website URL; site-only mode opens the website and does not create media directly in Telegram.
- Up to seven saved conversations, titles derived from the first message, and Iran-local display time for Persian users.
- Admin panel for users, broadcasts, chat backup/restore, model management, sponsor channels, and statistics.
- Group triggers, reply-based moderation, bot mute/unmute, and group lock/unlock.
- Persian and English UI.

### Web search note

This release does **not** include a standalone Google/Bing/Brave/SearXNG search menu. Web browsing is attempted only through supported native search tools provided by a compatible selected AI API.

## Requirements

- Python 3.10+ recommended
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Numeric admin Telegram user ID
- Upstash Redis REST URL and token
- Provider API credentials for models that require them

## Setup

1. Create an Upstash Redis database and copy its REST URL and REST token.
2. Configure these environment variables in your hosting dashboard:

   | Variable | Description |
   |---|---|
   | `BOT_TOKEN` | Telegram bot token |
   | `ADMIN_ID` | Numeric Telegram user ID of the main admin |
   | `UPSTASH_URL` | Upstash Redis REST endpoint |
   | `UPSTASH_TOKEN` | Upstash Redis REST token |

3. Install dependencies and run:

   ```bash
   python -m pip install -r requirements.txt
   python main.py
   ```

`main.py` and `Bot_Ai_Beta_5_Model_Banner.py` contain the same source. The `.env.example` file is a reference only: the script reads operating-system environment variables and does not load `.env` automatically.

## Configure models

Open `/start` in a private chat and use the Admin Panel. Enter the endpoint, API key, and model ID exactly as specified by each provider. For image/video models, a normal website URL is not a substitute for a provider API. If only a website URL is configured for video, the bot opens that site rather than generating the video inside Telegram.

## Group commands

- Call the bot with a supported prefix such as `ربات ...`, `بات ...`, `نئو ...`, `neo ...`, or `tenet ...`.
- Reply to a user's message with `سکوت`, `سکوت 10`, `رفع سکوت`, `اخراج`, `بن`, `حذف`, or `پاک`.
- `/bot سکوت` and `/bot صحبت` pause/resume bot responses in the group.
- `/lock` / `/close` lock the group; `/unlock` / `/open` unlock it, if the bot has permissions.
- `/models` opens model selection subject to the version's access checks.

Moderation commands require suitable group-admin status and Telegram permissions for the bot.

## Security

Do not commit Telegram tokens, Redis credentials, or provider API keys. Store credentials in your host's secret/environment settings. User history and settings are persisted in Upstash Redis, so deploy only with an appropriate data-retention policy.

## Links

- [Project repository](https://github.com/NeoTenet/Neo-Ai-Bot-Python)
- [Telegram channel](https://t.me/NeoTenet)
- [Issues](https://github.com/NeoTenet/Neo-Ai-Bot-Python/issues)
