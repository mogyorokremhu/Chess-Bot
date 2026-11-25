"""Plays a single game."""
from __future__ import annotations

import logging

import chess

log = logging.getLogger(__name__)


class Game:
    def __init__(self, client, engine_factory, game_id: str, bot_id: str, chat_cfg: dict) -> None:
        self.client = client
        self.engine_factory = engine_factory
        self.game_id = game_id
        self.bot_id = bot_id.lower()
        self.chat_cfg = chat_cfg
        self.color: chess.Color | None = None

    @staticmethod
    def _board_from(full: dict, moves: str) -> chess.Board:
        fen = full.get("initialFen", "startpos")
        board = chess.Board() if fen in (None, "startpos") else chess.Board(fen)
        for uci in moves.split():
            board.push_uci(uci)
        return board

    def run(self) -> None:
        engine = None
        try:
            engine = self.engine_factory()
            full = None
            for event in self.client.stream_game(self.game_id):
                kind = event.get("type")
                if kind == "gameFull":
                    full = event
                    self.color = chess.WHITE if event["white"].get("id", "").lower() == self.bot_id else chess.BLACK
                    self.client.chat(self.game_id, self.chat_cfg.get("greeting", ""))
                    state = event["state"]
                elif kind == "gameState" and full is not None:
                    state = event
                else:
                    continue
                if state["status"] != "started":
                    log.info("Game %s finished: %s", self.game_id, state["status"])
                    self.client.chat(self.game_id, self.chat_cfg.get("goodbye", ""))
                    return
                board = self._board_from(full, state["moves"])
                if board.turn == self.color and not board.is_game_over():
                    move = engine.best_move(
                        board, state["wtime"], state["btime"], state.get("winc", 0), state.get("binc", 0)
                    )
                    self.client.make_move(self.game_id, move.uci())
        except Exception:
            log.exception("Game %s crashed", self.game_id)
        finally:
            if engine is not None:
                engine.close()
