import logging
import typing

from odoo import api

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return
    env = api.Environment(cr, api.SUPERUSER_ID, {})
    _clear_blocks_on_non_internal_locations(env)
    _resync_effective_block_type(env)
    _warn_about_blocks_with_no_reason(env)


def _clear_blocks_on_non_internal_locations(env: api.Environment) -> None:
    offending = (
        env["stock.location"]
        .with_context(active_test=False)
        .search(
            [
                ("block_type", "!=", "none"),
                ("usage", "not in", ["internal"]),
            ],
        )
    )
    for location in offending:
        _logger.warning(
            "stock 1.13: clearing the %s block on %s, which is a %s location -- "
            "only internal locations can be blocked",
            location.block_type,
            location.display_name,
            location.usage,
        )
    if offending:
        offending.write({"block_type": "none"})


def _resync_effective_block_type(env: api.Environment) -> None:
    locations = env["stock.location"].with_context(active_test=False).search([])
    locations.modified(["block_type"])
    env.flush_all()


def _warn_about_blocks_with_no_reason(env: api.Environment) -> None:
    unexplained = (
        env["stock.location"]
        .with_context(active_test=False)
        .search([("block_type", "!=", "none"), ("block_reason", "in", [False, ""])])
    )
    if not unexplained:
        return
    _logger.warning(
        "stock 1.13: %d blocked location(s) carry no blocking reason. The "
        "location form requires one, so the next manual save of each will ask",
        len(unexplained),
    )
    for location in unexplained:
        _logger.warning(
            "stock 1.13: %s is %s with no reason recorded",
            location.display_name,
            location.block_type,
        )
