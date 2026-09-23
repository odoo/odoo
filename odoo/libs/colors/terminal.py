from typing import Final

__all__ = [
    "BLACK",
    "BLUE",
    "CYAN",
    "DEFAULT",
    "GREEN",
    "MAGENTA",
    "RED",
    "WHITE",
    "YELLOW",
    "colorize",
]

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, _NOTHING, DEFAULT = range(10)

_RESET_SEQ: Final[str] = "\033[0m"
_COLOR_SEQ: Final[str] = "\033[1;%dm"
_COLOR_PATTERN: Final[str] = f"{_COLOR_SEQ}{_COLOR_SEQ}%s{_RESET_SEQ}"


def colorize(text: str, fg: int = DEFAULT, bg: int = DEFAULT) -> str:
    return _COLOR_PATTERN % (30 + fg, 40 + bg, text)
