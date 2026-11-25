"""Entry point: python -m lichess_bot"""
from __future__ import annotations

import argparse
import logging
import random
import threading
import time

from . import __version__
from .api import LichessClient
from .challenges import evaluate
from .config import get_token, load_config
from .engine import Engine
from .game import Game

log = logging.getLogger("lichess_bot")


class Bot:
    def __init__(self, cfg: dict, client: LichessClient) -> None:
        self.cfg = cfg
        self.client = client
        self.active: dict[str, threading.Thread] = {}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.me: dict = {}

    def _active_count(self) -> int:
        with self.lock:
            self.active = {k: t for k, t in self.active.items() if t.is_alive()}
            return len(self.active)

    def start_game(self, game_id: str) -> None:
        with self.lock:
            if game_id in self.active:
                return
            game = Game(self.client, lambda: Engine(self.cfg["engine"]), game_id, self.me["id"], self.cfg["chat"])
            t = threading.Thread(target=game.run, name=f"game-{game_id}", daemon=True)
            self.active[game_id] = t
            t.start()
        log.info("Started game %s", game_id)

    def handle_event(self, event: dict) -> None:
        kind = event.get("type")
        if kind == "challenge":
            ch = event["challenge"]
            if ch.get("challenger", {}).get("id", "").lower() == self.me["id"].lower():
                return  # our own outgoing challenge
            reason = evaluate(ch, self.cfg["challenges"], self._active_count())
            if reason is None:
                log.info("Accepting challenge %s", ch["id"])
                self.client.accept_challenge(ch["id"])
            else:
                log.info("Declining challenge %s (%s)", ch["id"], reason)
                self.client.decline_challenge(ch["id"], reason)
        elif kind == "gameStart":
            self.start_game(event["game"].get("gameId") or event["game"]["id"])

    def matchmaking_loop(self) -> None:
        mm = self.cfg["matchmaking"]
        while not self.stop.wait(mm["interval_seconds"]):
            if self._active_count() >= self.cfg["challenges"]["max_concurrent_games"]:
                continue
            try:
                bots = [b for b in self.client.online_bots() if b["id"] != self.me["id"]]
                my_rating = self.me.get("perfs", {}).get("blitz", {}).get("rating", 1500)
                bots = [
                    b for b in bots
                    if abs(b.get("perfs", {}).get("blitz", {}).get("rating", my_rating) - my_rating) <= mm["rating_window"]
                ]
                if bots:
                    target = random.choice(bots)["username"]
                    log.info("Challenging %s", target)
                    self.client.create_challenge(
                        target, rated=mm["rated"], limit=mm["initial_seconds"], increment=mm["increment_seconds"]
                    )
            except Exception:
                log.exception("Matchmaking failed")

    def run(self) -> None:
        self.me = self.client.account()
        if self.me.get("title") != "BOT":
            raise SystemExit(
                "This account is not a BOT account. Run with --upgrade (irreversible, and only possible "
                "on accounts that have never played a game). See README."
            )
        log.info("Logged in as %s", self.me["username"])
        if self.cfg["matchmaking"]["enabled"]:
            threading.Thread(target=self.matchmaking_loop, daemon=True).start()
        backoff = 1
        while not self.stop.is_set():
            try:
                for event in self.client.stream_events():
                    backoff = 1
                    self.handle_event(event)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                log.warning("Event stream dropped (%s); reconnecting in %ss", exc, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)


def main() -> None:
    p = argparse.ArgumentParser(prog="lichess_bot", description="Lichess Bot API client powered by a UCI engine")
    p.add_argument("-c", "--config", default="config.yml", help="path to config (default: config.yml)")
    p.add_argument("--upgrade", action="store_true", help="upgrade the token's account to a BOT account (irreversible)")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        log.warning("%s not found, using defaults", args.config)
        cfg = load_config(None)
    client = LichessClient(get_token())

    if args.upgrade:
        if input("Upgrade to BOT account? This is IRREVERSIBLE. Type 'yes': ").strip() == "yes":
            print("Upgraded." if client.upgrade_to_bot() else "Upgrade failed (account must have played 0 games).")
        return

    bot = Bot(cfg, client)
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopping; waiting for no new games. Ongoing games will be abandoned.")
        bot.stop.set()


if __name__ == "__main__":
    main()
