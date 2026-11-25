"""Minimal Lichess Bot API client (https://lichess.org/api#tag/Bot)."""
from __future__ import annotations

import json
import logging
import time
from typing import Iterator

import requests

log = logging.getLogger(__name__)


class LichessClient:
    def __init__(self, token: str, base_url: str = "https://lichess.org") -> None:
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["User-Agent"] = "lichess-bot-python/0.1"

    # -- helpers -----------------------------------------------------------
    def _request(self, method: str, path: str, retries: int = 3, **kw) -> requests.Response:
        for attempt in range(retries):
            resp = self.session.request(method, self.base + path, timeout=kw.pop("timeout", 30), **kw)
            if resp.status_code == 429:  # rate limited: lichess asks for a 1 min pause
                log.warning("Rate limited, sleeping 60s")
                time.sleep(60)
                continue
            if resp.status_code >= 500 and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return resp
        return resp

    def _stream(self, path: str) -> Iterator[dict]:
        with self.session.get(self.base + path, stream=True, timeout=(10, 90)) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    yield json.loads(line)

    # -- account -----------------------------------------------------------
    def account(self) -> dict:
        resp = self._request("GET", "/api/account")
        resp.raise_for_status()
        return resp.json()

    def upgrade_to_bot(self) -> bool:
        return self._request("POST", "/api/bot/account/upgrade").ok

    # -- events / games ----------------------------------------------------
    def stream_events(self) -> Iterator[dict]:
        return self._stream("/api/stream/event")

    def stream_game(self, game_id: str) -> Iterator[dict]:
        return self._stream(f"/api/bot/game/stream/{game_id}")

    def make_move(self, game_id: str, move: str) -> bool:
        resp = self._request("POST", f"/api/bot/game/{game_id}/move/{move}")
        if not resp.ok:
            log.error("Move %s rejected in %s: %s", move, game_id, resp.text)
        return resp.ok

    def resign(self, game_id: str) -> bool:
        return self._request("POST", f"/api/bot/game/{game_id}/resign").ok

    def chat(self, game_id: str, text: str) -> None:
        if text:
            self._request("POST", f"/api/bot/game/{game_id}/chat", data={"room": "player", "text": text})

    # -- challenges --------------------------------------------------------
    def accept_challenge(self, challenge_id: str) -> bool:
        return self._request("POST", f"/api/challenge/{challenge_id}/accept").ok

    def decline_challenge(self, challenge_id: str, reason: str = "generic") -> bool:
        return self._request("POST", f"/api/challenge/{challenge_id}/decline", data={"reason": reason}).ok

    def create_challenge(self, username: str, *, rated: bool, limit: int, increment: int) -> bool:
        data = {"rated": str(rated).lower(), "clock.limit": limit, "clock.increment": increment}
        return self._request("POST", f"/api/challenge/{username}", data=data).ok

    def online_bots(self, count: int = 50) -> list[dict]:
        resp = self._request("GET", f"/api/bot/online?nb={count}", timeout=60)
        resp.raise_for_status()
        return [json.loads(l) for l in resp.text.splitlines() if l.strip()]
