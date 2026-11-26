import chess

from lichess_bot.challenges import evaluate
from lichess_bot.config import DEFAULTS, load_config
from lichess_bot.engine import move_time
from lichess_bot.game import Game

CH = DEFAULTS["challenges"]


def challenge(**kw):
    base = {"id": "x", "challenger": {"id": "bob", "name": "bob"}, "variant": {"key": "standard"},
            "rated": False, "speed": "blitz", "timeControl": {"type": "clock", "limit": 180, "increment": 2}}
    base.update(kw)
    return base


def test_accepts_normal():
    assert evaluate(challenge(), CH, 0) is None


def test_busy_declines_later():
    assert evaluate(challenge(), CH, CH["max_concurrent_games"]) == "later"


def test_variant_and_time():
    assert evaluate(challenge(variant={"key": "atomic"}), CH, 0) == "variant"
    tc = {"type": "clock", "limit": 10, "increment": 0}
    assert evaluate(challenge(timeControl=tc, speed="bullet"), CH, 0) == "tooFast"


def test_blocklist():
    cfg = dict(CH, blocklist=["Bob"])
    assert evaluate(challenge(), cfg, 0) == "generic"


def test_humans_only():
    cfg = dict(CH, **{"from": "humans"})
    ch = challenge(challenger={"id": "b", "name": "b", "title": "BOT"})
    assert evaluate(ch, cfg, 0) == "onlyHuman"


def test_move_time_bounds():
    cfg = DEFAULTS["engine"]
    assert move_time(1000, 0, cfg) >= cfg["min_move_time"]
    assert move_time(10_000_000, 0, cfg) == cfg["max_move_time"]


def test_config_validation(tmp_path):
    p = tmp_path / "c.yml"
    p.write_text("engine:\n  elo: 5\n")
    try:
        load_config(str(p))
        assert False
    except ValueError:
        pass


class FakeEngine:
    def best_move(self, board, *a):
        return next(iter(board.legal_moves))

    def close(self):
        pass


class FakeClient:
    def __init__(self, events):
        self.events, self.moves, self.chats = events, [], []

    def stream_game(self, _):
        return iter(self.events)

    def make_move(self, gid, mv):
        self.moves.append(mv)

    def chat(self, gid, text):
        self.chats.append(text)


def test_game_plays_when_its_turn():
    full = {"type": "gameFull", "white": {"id": "me"}, "black": {"id": "opp"}, "initialFen": "startpos",
            "state": {"moves": "", "status": "started", "wtime": 60000, "btime": 60000}}
    over = {"type": "gameState", "moves": "e2e4", "status": "mate", "wtime": 1, "btime": 1}
    client = FakeClient([full, over])
    Game(client, FakeEngine, "g1", "me", {"greeting": "hi", "goodbye": "gg"}).run()
    assert len(client.moves) == 1
    assert chess.Move.from_uci(client.moves[0]) in chess.Board().legal_moves
    assert client.chats == ["hi", "gg"]


def test_game_waits_when_not_its_turn():
    full = {"type": "gameFull", "white": {"id": "opp"}, "black": {"id": "me"}, "initialFen": "startpos",
            "state": {"moves": "", "status": "started", "wtime": 60000, "btime": 60000}}
    client = FakeClient([full])
    Game(client, FakeEngine, "g1", "me", {}).run()
    assert client.moves == []


def test_env_overrides():
    cfg = load_config(None, env={"BOT_ENGINE_ELO": "2200", "BOT_MAX_GAMES": "3",
                                 "BOT_MATCHMAKING": "true", "BOT_ACCEPT_FROM": "bots"})
    assert cfg["engine"]["elo"] == 2200
    assert cfg["challenges"]["max_concurrent_games"] == 3
    assert cfg["challenges"]["from"] == "bots"
    assert cfg["matchmaking"]["enabled"] is True
    assert load_config(None, env={"BOT_ENGINE_ELO": "full"})["engine"]["elo"] is None
