import logging
from typing import Any

from .debug_log import format_event

__all__ = ["ASSET_ROOT", "get_asset_logger", "log_event"]

ASSET_ROOT = "odoo.assets"


def get_asset_logger(category: str) -> logging.Logger:
    if not category:
        return logging.getLogger(ASSET_ROOT)
    return logging.getLogger(f"{ASSET_ROOT}.{category}")


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    if logger.isEnabledFor(level):
        logger.log(level, "%s", format_event(event, fields))
