# VPNIC Telegram Shop Bot (Python)

A starter Telegram shop bot using Python and `python-telegram-bot`.

## Features
- Mandatory membership check for four channels.
- Four products with minimum quantities and prices configured in `main.py`.
- Card-to-card payment instructions from environment variables.
- User sends receipt photo; manager gets it with Approve/Reject buttons.
- After payment approval, manager can manually send the config/panel details to the buyer.
- SQLite order tracking and `/start`, `/cancel` commands.

## Important setup
1. Create a bot with Telegram's `@BotFather` and copy its token.
2. Get your numeric Telegram user ID and set it as `ADMIN_ID`.
3. Add the bot as an administrator to all four required channels so it can check membership.
4. Copy `.env.example` to `.env` and fill in the values.
5. Never upload `.env` or your bot token to GitHub.

## Run locally on Windows
Install Python 3.11 or newer, then open CMD in this folder and run:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
copy .env.example .env
notepad .env
py main.py
```

Edit `.env` and replace the placeholder values before running.

## Upload to GitHub
Create a **Private** repository. Upload `main.py`, `requirements.txt`, `.env.example`, `.gitignore`, and `README.md`.
Do not upload `.env`, `orders.db`, or any secret.

## Hosting notes
The bot uses long polling, so it needs a Python process that stays running. A notebook session such as Molab is useful for testing but should not be treated as guaranteed 24/7 hosting. Check your host's current Python support and sleep/restart policy.

## Important limitations
- The bot does **not** verify bank transfers automatically; a manager must inspect each receipt.
- Config/panel delivery is manual in this starter. Automatic provisioning requires the exact API documentation and credentials for your Pasarguard installation; do not paste API secrets into GitHub.
- Membership checking can fail unless the bot has appropriate access to the required channels.
- This starter is not a guarantee of secure or production-ready payment handling.
