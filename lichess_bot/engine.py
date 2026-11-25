"""UCI engine wrapper and time management."""
from __future__ import annotations

import chess
import chess.engine


def move_time(remaining_ms: int, increment_ms: int, cfg: dict) -> float:
    """Seconds to think for one move."""
    secs = remaining_ms / 1000 / cfg["moves_left_estimate"] + increment_ms / 1000 * cfg["inc_fraction"]
    # never spend more than a third of what's left
    secs = min(secs, remaining_ms / 1000 / 3)
    return max(cfg["min_move_time"], min(secs, cfg["max_move_time"]))


class Engine:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.engine = chess.engine.SimpleEngine.popen_uci(cfg["path"])
        options: dict = {}
        if "Threads" in self.engine.options:
            options["Threads"] = cfg["threads"]
        if "Hash" in self.engine.options:
            options["Hash"] = cfg["hash_mb"]
        elo = cfg.get("elo")
        if elo is not None and "UCI_LimitStrength" in self.engine.options:
            opt = self.engine.options.get("UCI_Elo")
            if opt is not None:
                if opt.min is not None:
                    elo = max(opt.min, elo)
                if opt.max is not None:
                    elo = min(opt.max, elo)
            options["UCI_LimitStrength"] = True
            options["UCI_Elo"] = elo
        self.engine.configure(options)

    def best_move(self, board: chess.Board, wtime: int, btime: int, winc: int, binc: int) -> chess.Move:
        remaining, inc = (wtime, winc) if board.turn == chess.WHITE else (btime, binc)
        limit = chess.engine.Limit(time=move_time(remaining, inc, self.cfg))
        return self.engine.play(board, limit).move

    def close(self) -> None:
        try:
            self.engine.quit()
        except Exception:
            self.engine.close()
