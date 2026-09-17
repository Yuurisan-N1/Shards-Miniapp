<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=ShardsEarn%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Auto%20Tasks%20%7C%20Auto%20Ads%20%7C%20Lucky%20Chest%20%7C%20Tic%20Tac%20Toe%20%7C%20Multi-Account&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Auto+Social+Tasks+%7C+Claim+Shard+Rewards;Auto+Ad+Tasks+%7C+Multi-View+Ad+Rewards;Auto+Earn+More+%7C+Step+by+Step+Ad+Progression;Auto+Lucky+Chest+%7C+Purchase+and+Open+Chest;Auto+Tic+Tac+Toe+%7C+Minimax+AI+Player;Proxy+Support+%7C+One+Proxy+Per+Account;Multi-Account+%7C+Sequential+Processing+Per+Cycle"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-ShardsEarn%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>ShardsEarn Miniapp Bot</b> is a full automation bot for the ShardsEarn Telegram Miniapp.<br/>
  It handles the complete daily cycle: authenticating each account, completing all pending social tasks, processing multi-view ad tasks and earn more ad steps, purchasing and opening the lucky chest, and playing tic tac toe with a minimax AI solver to maximize wins, all running across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Shards-Miniapp.git
cd Shards-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

Lines starting with `#` are treated as comments and skipped.

> `initData` can be obtained from the browser DevTools when opening ShardsEarn on Telegram Web.

### 2. Proxy (proxy.txt) - Optional

Fill `proxy.txt` with proxies, one per line. Proxies are assigned to accounts by index (first proxy to first account, second proxy to second account, and so on). If the number of proxies is fewer than the number of accounts, proxies wrap around cyclically. If `proxy.txt` is missing or empty, the bot runs without a proxy. Lines starting with `#` are treated as comments and skipped.

```
http://user:pass@ip:port
http://user:pass@ip:port
```

Supported formats: `http://user:pass@host:port` or `host:port:user:pass`

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, the bot falls back to a default of `3000` seconds.

```json
{
  "settings": {
    "sleep_seconds": 3000
  }
}
```

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Auto Login
The bot authenticates each account by sending the `initData` string to the auth endpoint. The username, current shard balance, leaderboard rank, total participants, and referral count are resolved from the dashboard and logged before any further actions are taken. If authentication fails, the account is skipped for that cycle.

### Auto Social Tasks
The bot fetches the full task list from the earn page and filters for pending social tasks that have not yet been approved. For each pending task, a completion request is sent and the reward status is logged. Tasks that are already completed, still being verified by the server, or blocked by a membership requirement are each logged separately and skipped without stopping the rest.

### Auto Ad Tasks
The bot processes multi-view ad tasks from the earn page. For each task, it repeatedly serves ads through the Adsgram network until all remaining views for that task are credited. Each credited view and its shard reward are logged individually. A captcha challenge is automatically requested and solved using SVG shape matching whenever the ad network requires verification before the next ad can be served.

### Auto Earn More
The bot processes the earn more progression step by step, claiming each reward as it becomes available. Both ad-backed steps and direct dwell steps are handled. If a cooldown or penalty timer is active between steps, the bot waits for it to expire before continuing. Progress, steps completed, and shards claimed are logged after the earn more run finishes for each account.

### Auto Lucky Chest
The bot checks whether a lucky chest is already active and ready to open. If one is active, an ad is served and the chest is opened immediately. If no chest is active and the cooldown has passed, the bot checks the shard balance against the chest price, serves an ad to purchase, then serves a second ad to open it. The shard reward and bonus percent are logged on a successful open.

### Auto Tic Tac Toe
The bot checks for any unclaimed or active games from a previous session and handles them before starting a new one. New games are started by serving an ad and then played out automatically using a minimax solver that always picks the optimal move. Once the game ends, another ad is served to claim the shard reward. The outcome and reward paid are logged after each game.

### Proxy Support
Each account can be assigned its own proxy via `proxy.txt`. If a proxy is configured for the current account, it is shown in masked form before processing begins. Proxy assignment uses a round-robin fallback if there are fewer proxies than accounts. Both `http://user:pass@host:port` and `host:port:user:pass` formats are supported.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Account index, username, shard balance, rank, and referral count are logged at the start of each account. Final shard balance is logged after all actions complete. A blank line separates each account output in the terminal for readability.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown in the terminal until the next cycle starts, then re-shows the banner before beginning again.

---

## File Structure

```text
Shards-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxies, one per line (optional)
├── LICENSE         # License file
└── utils/
    ├── banner.py   # Banner display on startup
    └── __init__.py
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>