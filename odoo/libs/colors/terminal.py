from typing import Final

__all__ = [
    "BLACK",
    "BLUE",
    "COLOR_PATTERN",
    "COLOR_SEQ",
    "CYAN",
    "DEFAULT",
    "GREEN",
    "MAGENTA",
    "RED",
    "RESET_SEQ",
    "WHITE",
    "YELLOW",
    "colorize",
]

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, _NOTHING, DEFAULT = range(10)

RESET_SEQ: Final[str] = "\033[0m"
COLOR_SEQ: Final[str] = "\033[1;%dm"
COLOR_PATTERN: Final[str] = f"{COLOR_SEQ}{COLOR_SEQ}%s{RESET_SEQ}"


def colorize(text: str, fg: int = DEFAULT, bg: int = DEFAULT) -> str:
    return COLOR_PATTERN % (30 + fg, 40 + bg, text)
