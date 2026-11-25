"""Decide whether to accept an incoming challenge."""
from __future__ import annotations


def evaluate(challenge: dict, cfg: dict, active_games: int, friends: set[str] | None = None) -> str | None:
    """Return None to accept, or a Lichess decline reason key."""
    c = cfg
    challenger = challenge.get("challenger") or {}
    name = (challenger.get("name") or challenger.get("id") or "").lower()
    allow = {n.lower() for n in c["allowlist"]}
    block = {n.lower() for n in c["blocklist"]}

    if name in block:
        return "generic"
    if name in allow:
        return None if active_games < c["max_concurrent_games"] else "later"
    if not c["accept"]:
        return "generic"
    if active_games >= c["max_concurrent_games"]:
        return "later"

    is_bot = challenger.get("title") == "BOT"
    who = c["from"]
    if who == "bots" and not is_bot:
        return "noBot"
    if who == "humans" and is_bot:
        return "onlyHuman"
    if who == "friends" and name not in (friends or set()):
        return "generic"

    if challenge.get("variant", {}).get("key") not in c["variants"]:
        return "variant"
    rated = challenge.get("rated", False)
    if rated and not c["accept_rated"]:
        return "casual"
    if not rated and not c["accept_casual"]:
        return "rated"

    tc = challenge.get("timeControl", {})
    if tc.get("type") != "clock":
        return "timeControl"
    if challenge.get("speed") not in c["time_controls"]:
        return "timeControl"
    if not (c["min_initial_seconds"] <= tc.get("limit", 0) <= c["max_initial_seconds"]):
        return "tooFast" if tc.get("limit", 0) < c["min_initial_seconds"] else "tooSlow"
    if tc.get("increment", 0) > c["max_increment_seconds"]:
        return "timeControl"
    return None
