"""NameEngine — Core logic: loads names, per-name cooldown, random draw."""

import random
import time
from datetime import datetime

from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class NameEngine(QObject):
    """Non-UI logic: loads names, draws randomly, per-name cooldown.

    Cooldown model: each drawn name gets a 10-min cooldown.
    Other names can still be drawn immediately.
    """

    # --- Signals ---
    name_drawn = pyqtSignal(str)          # (name) — final result after rolling
    rolling_start = pyqtSignal(str)       # (name) — engine picked a name, start rolling animation
    names_loaded = pyqtSignal(int)        # (count)
    error_occurred = pyqtSignal(str)      # (message)
    history_cleared = pyqtSignal()
    pool_refilled = pyqtSignal(int)       # (pool_size)
    cooldowns_updated = pyqtSignal()      # per-name cooldowns changed (for UI refresh)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._names: list[str] = []
        self._remaining_names: list[str] = []       # draws w/o repeat (resets when empty)
        self._history: list[tuple[str, datetime]] = []
        self._cooldown_seconds: int = 600            # 10 min per name (configurable)
        self._per_name_cooldown: dict[str, float] = {}  # name -> eligible_timestamp

    def load_names_from_file(self, filepath: str) -> bool:
        """Load UTF-8 text file, one name per line. # comments and blanks skipped."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._names = [
                    line.strip() for line in f
                    if line.strip() and not line.strip().startswith('#')
                ]
        except FileNotFoundError:
            self.error_occurred.emit(f"文件不存在: {filepath}")
            return False
        except PermissionError:
            self.error_occurred.emit(f"没有权限读取文件: {filepath}")
            return False
        except UnicodeDecodeError:
            self.error_occurred.emit("文件编码不是 UTF-8，请用 UTF-8 保存名单文件。")
            return False
        except OSError as e:
            self.error_occurred.emit(f"读取文件失败: {e}")
            return False

        if not self._names:
            self.error_occurred.emit("文件中没有找到任何名字。")
            return False

        self._remaining_names = list(self._names)
        self._history.clear()
        self._per_name_cooldown.clear()

        self.names_loaded.emit(len(self._names))
        self.history_cleared.emit()
        self.cooldowns_updated.emit()
        return True

    def generate_number_list(self, start: int, end: int) -> None:
        """Generate a numeric name list from start to end (inclusive)."""
        if start > end:
            start, end = end, start
        self._names = [str(i) for i in range(start, end + 1)]
        self._remaining_names = list(self._names)
        self._history.clear()
        self._per_name_cooldown.clear()

        self.names_loaded.emit(len(self._names))
        self.history_cleared.emit()
        self.cooldowns_updated.emit()

    def draw_name(self) -> str | None:
        """Pick a random name avoiding per-name cooldown. Returns None if all cooling."""
        if not self._names:
            self.error_occurred.emit("请先加载名单文件。")
            return None

        now = time.time()

        # Build available pool from remaining_names, filtering by cooldown
        available = [
            n for n in self._remaining_names
            if self._per_name_cooldown.get(n, 0) <= now
        ]

        # If nothing available in current cycle, try refilling first
        if not available:
            # Expand to all names (allow redrawing cooldowned if necessary)
            all_available = [
                n for n in self._names
                if self._per_name_cooldown.get(n, 0) <= now
            ]
            if all_available:
                # Refill remaining from all available
                self._remaining_names = list(all_available)
                available = all_available
                self.pool_refilled.emit(len(self._remaining_names))
            else:
                # Everything is in cooldown — find the name that frees up soonest
                best_name = min(self._names, key=lambda n: self._per_name_cooldown.get(n, 0))
                wait_secs = int(self._per_name_cooldown.get(best_name, 0) - now)
                wait_m = wait_secs // 60
                wait_s = wait_secs % 60
                self.error_occurred.emit(
                    f"所有名字都在冷却中！\n最快可用：{best_name}（{wait_m}分{wait_s:02d}秒后）"
                )
                return None

        # Draw from available
        name = random.choice(available)
        self._remaining_names.remove(name)

        # Refill remaining if empty
        if not self._remaining_names:
            self._remaining_names = list(self._names)
            self.pool_refilled.emit(len(self._remaining_names))

        # Apply per-name cooldown
        self._per_name_cooldown[name] = now + self._cooldown_seconds

        # Record history
        self._history.append((name, datetime.now()))

        # Emit signals — rolling first, then after a delay the result
        self.rolling_start.emit(name)
        self.name_drawn.emit(name)
        self.cooldowns_updated.emit()

        return name

    def set_cooldown(self, minutes: int) -> None:
        """Set per-name cooldown duration in minutes."""
        self._cooldown_seconds = max(1, minutes) * 60

    def get_cooldown_seconds(self) -> int:
        return self._cooldown_seconds

    def get_per_name_cooldowns(self) -> dict[str, int]:
        """Return {name: remaining_seconds} for names currently in cooldown."""
        now = time.time()
        return {
            name: max(0, int(ts - now))
            for name, ts in self._per_name_cooldown.items()
            if ts > now
        }

    def get_names(self) -> list[str]:
        return list(self._names)

    def get_history(self) -> list[tuple[str, str]]:
        """Return history as list of (name, timestamp_str). Newest first."""
        return [(name, dt.strftime('%Y-%m-%d %H:%M:%S'))
                for name, dt in reversed(self._history)]

    def clear_history(self) -> None:
        self._history.clear()
        self._per_name_cooldown.clear()
        self._remaining_names = list(self._names)
        self.history_cleared.emit()
        self.cooldowns_updated.emit()

    def get_remaining_count(self) -> int:
        return len(self._remaining_names)

    def get_total_count(self) -> int:
        return len(self._names)

    def is_numeric_list(self) -> bool:
        """Return True if all names are pure digits (number range mode)."""
        if not self._names:
            return True  # empty = default numeric mode
        return all(s.lstrip('-').isdigit() for s in self._names)
