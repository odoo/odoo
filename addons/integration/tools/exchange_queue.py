import logging
from typing import Any

from odoo import api

_logger = logging.getLogger(__name__)

PENDING_KEY = "integration.exchange.values"


def queue_exchange_values(env: api.Environment, vals: dict[str, Any]) -> None:
    cr = env.cr
    if PENDING_KEY not in cr.precommit.data:
        _register_flush_hooks(env)
    cr.precommit.data[PENDING_KEY].append(vals)


def _register_flush_hooks(env: api.Environment) -> None:
    cr = env.cr
    pending = cr.precommit.data[PENDING_KEY] = []
    registry = env.registry
    uid = env.uid

    @cr.precommit.add
    def batch_create_logs():
        logs = cr.precommit.data.pop(PENDING_KEY, pending)
        if logs:
            env["integration.exchange"].sudo().create(
                _without_vanished_connections(env, logs)
            )
            _logger.debug("Batch created %d exchange rows", len(logs))

    # A caller that lets an error propagate rolls its transaction back, and the
    # exchange that failed is the one most worth a row. `_rollback` empties
    # `precommit.data` before running this, so it keeps its own list.
    @cr.postrollback.add
    def keep_logs_of_rolled_back_transaction():
        if not pending:
            return
        try:
            with registry.cursor() as log_cr:
                log_env = api.Environment(log_cr, uid, {})
                log_env["integration.exchange"].sudo().create(
                    _without_vanished_connections(log_env, pending)
                )
        except Exception:
            _logger.exception(
                "Could not keep %d exchange row(s) of a rolled-back transaction",
                len(pending),
            )


def _without_vanished_connections(
    env: api.Environment, logs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Unlink rows from a connection that a rollback took away.

    A record's connection is created lazily in the transaction of its first
    call. When a savepoint or the transaction around that call rolls back, the
    connection goes with it while the call's queued row survives.
    """
    ids = {vals["connection_id"] for vals in logs if vals.get("connection_id")}
    if not ids:
        return list(logs)
    present = set(env["integration.connection"].sudo().browse(ids).exists().ids)
    return [
        {**vals, "connection_id": False}
        if vals.get("connection_id") and vals["connection_id"] not in present
        else vals
        for vals in logs
    ]
