"""Configuration loading."""
from __future__ import annotations

import copy
import os
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "engine": {
        "path": "stockfish",
        "elo": 1800,
        "threads": 1,
        "hash_mb": 64,
        "moves_left_estimate": 30,
        "inc_fraction": 0.5,
        "min_move_time": 0.05,
        "max_move_time": 10.0,
    },
    "challenges": {
        "accept": True,
        "from": "everyone",
        "accept_rated": True,
        "accept_casual": True,
        "variants": ["standard"],
        "time_controls": ["bullet", "blitz", "rapid", "classical"],
        "min_initial_seconds": 30,
        "max_initial_seconds": 1800,
        "max_increment_seconds": 30,
        "max_concurrent_games": 2,
        "blocklist": [],
        "allowlist": [],
    },
    "matchmaking": {
        "enabled": False,
        "rated": False,
        "initial_seconds": 180,
        "increment_seconds": 2,
        "interval_seconds": 120,
        "rating_window": 300,
    },
    "chat": {"greeting": "Hi! I'm a bot. Good luck!", "goodbye": "Good game!"},
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


# Environment variable -> (section, key, type). Handy for cloud hosts with no config file.
ENV_OVERRIDES = {
    "BOT_ENGINE_ELO": ("engine", "elo", "int_or_none"),
    "BOT_ENGINE_THREADS": ("engine", "threads", int),
    "BOT_ENGINE_HASH_MB": ("engine", "hash_mb", int),
    "BOT_ACCEPT_FROM": ("challenges", "from", str),
    "BOT_MAX_GAMES": ("challenges", "max_concurrent_games", int),
    "BOT_ACCEPT_RATED": ("challenges", "accept_rated", "bool"),
    "BOT_ACCEPT_CASUAL": ("challenges", "accept_casual", "bool"),
    "BOT_MATCHMAKING": ("matchmaking", "enabled", "bool"),
    "BOT_MATCHMAKING_RATED": ("matchmaking", "rated", "bool"),
}


def _convert(raw: str, kind):
    if kind == "bool":
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if kind == "int_or_none":
        return None if raw.strip().lower() in {"", "none", "null", "full"} else int(raw)
    return kind(raw)


def apply_env(cfg: dict[str, Any], env=os.environ) -> None:
    for var, (section, key, kind) in ENV_OVERRIDES.items():
        if var in env:
            cfg[section][key] = _convert(env[var], kind)


def load_config(path: str | None, env=os.environ) -> dict[str, Any]:
    user: dict = {}
    if path:
        with open(path, encoding="utf-8") as fh:
            user = yaml.safe_load(fh) or {}
    cfg = _merge(DEFAULTS, user)
    apply_env(cfg, env)
    validate(cfg)
    return cfg


def validate(cfg: dict[str, Any]) -> None:
    ch = cfg["challenges"]
    if ch["from"] not in {"everyone", "bots", "humans", "friends"}:
        raise ValueError("challenges.from must be everyone, bots, humans or friends")
    if ch["max_concurrent_games"] < 1:
        raise ValueError("challenges.max_concurrent_games must be >= 1")
    elo = cfg["engine"]["elo"]
    if elo is not None and not (500 <= int(elo) <= 3500):
        raise ValueError("engine.elo must be null or between 500 and 3500")


def get_token() -> str:
    token = os.environ.get("LICHESS_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "LICHESS_TOKEN is not set. Create a token with the 'bot:play' scope at "
            "https://lichess.org/account/oauth/token/create and export it."
        )
    return token
