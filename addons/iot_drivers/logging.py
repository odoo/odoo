import logging.config
from typing import Any

# ANSI color codes
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

# Unicode icons
ICON_SUCCESS = "✅ "
ICON_ERROR = "❌ "
ICON_WARN = "⚠️"
ICON_INFO = "ℹ️"
ICON_DEBUG = "🐞 "


class IconFormatter(logging.Formatter):
    LEVEL_MAP = {
        logging.DEBUG: (f"{CYAN}{ICON_DEBUG}", CYAN),
        logging.INFO: (f"{GREEN}{ICON_INFO}", GREEN),
        logging.WARNING: (f"{YELLOW}{ICON_WARN}", YELLOW),
        logging.ERROR: (f"{RED}{ICON_ERROR}", RED),
        logging.CRITICAL: (f"{MAGENTA}{ICON_ERROR}", MAGENTA),
    }

    def format(self, record: logging.LogRecord):
        # Build timestamp and level prefix
        record_message = record.getMessage()
        asctime = self.formatTime(record, self.datefmt)
        level = record.levelname.ljust(8)
        prefix = f"{asctime} {level}"

        # Determine icon and color then build colored suffix
        icon, color = self.LEVEL_MAP.get(record.levelno, (ICON_INFO, RESET))
        suffix = f"{record.name}:{record.lineno}:{record.funcName}: {record_message}"
        colored = f"{color}{icon} {suffix}{RESET}"

        return f"{prefix} {colored}"


LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "icon": {
            "()": IconFormatter,
            "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "icon",
        },
    },
    "root": {
        "handlers": ["console"],
    },
}


logging.config.dictConfig(LOGGING)

_logger = logging.getLogger(__name__)
_logger.warning("==== Starting Odoo ====")
