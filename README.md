# Chess-Bot: Lichess bot

A bot for [Lichess](https://lichess.org) that uses the official
[Bot API](https://lichess.org/api#tag/Bot) and any UCI engine (Stockfish recommended).
It accepts challenges (and can optionally challenge other bots) and keeps playing until you stop it.
Runs locally or in the cloud (Docker).

> **Fair play:** Lichess only allows engine play from accounts upgraded to **BOT accounts**,
> which are clearly labelled as bots. Never use this on a normal account to play humans
> who don't know they're facing an engine. Don't use it on chess.com or any site that forbids bots.

## Setup

1. **Create a new Lichess account** and do **not** play any games on it.
   Upgrading to BOT is **irreversible** and only works on accounts with zero games played.
2. Create an API token with the **`bot:play`** scope (plus `challenge:write` for matchmaking):
   <https://lichess.org/account/oauth/token/create>
3. Install an engine, e.g. `sudo apt install stockfish` (or download from <https://stockfishchess.org>).
4. Install and configure:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp config.example.yml config.yml     # edit engine path, strength, challenge rules
   export LICHESS_TOKEN=lip_xxxxxxxx
   python -m lichess_bot --upgrade      # one time only, irreversible
   python -m lichess_bot                # run until Ctrl+C
   ```

## Docker / cloud

```bash
cp config.example.yml config.yml   # set engine.path to "stockfish" (installed in the image)
echo "LICHESS_TOKEN=lip_xxx" > .env
docker compose up -d --build
```
Works on any VPS or container host. Keep the token in an environment variable or secret store, never in the repo.

## Cloud from a phone (Railway)

1. Railway -> New Project -> Deploy from GitHub repo -> `Chess-Bot`, branch `lichess-bot`.
2. Service -> Variables: add `LICHESS_TOKEN` (token with `bot:play`). For a brand-new account with zero
   games also add `AUTO_UPGRADE=1` for the first deploy only, then delete it (the upgrade is permanent).
3. Optional variables (no config file needed): `BOT_ENGINE_ELO` (number or `full`), `BOT_ACCEPT_FROM`
   (`everyone|bots|humans|friends`), `BOT_MAX_GAMES`, `BOT_ACCEPT_RATED`, `BOT_ACCEPT_CASUAL`,
   `BOT_MATCHMAKING`, `BOT_MATCHMAKING_RATED`. These override `config.yml`.
4. Watch the Logs tab. The bot is a worker, so it opens no port.

## Configuration highlights (`config.yml`)

| Option | Meaning |
|---|---|
| `engine.elo` | Limit playing strength (null = full strength) |
| `challenges.from` | `everyone`, `bots`, `humans`, `friends` |
| `challenges.max_concurrent_games` | Parallel games |
| `challenges.blocklist` / `allowlist` | Per-user rules |
| `matchmaking.enabled` | Challenge other online bots automatically |

## Tests

```bash
pip install -r requirements-dev.txt && pytest
```

## Disclaimer

Provided as is. You are responsible for following Lichess's
[Terms of Service](https://lichess.org/terms-of-service) and bot rules. The author is not responsible
for account restrictions or any other consequences of using this software.

## License

Released under the [MIT License](LICENSE).
