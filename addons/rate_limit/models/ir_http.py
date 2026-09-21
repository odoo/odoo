import logging

from werkzeug.exceptions import TooManyRequests

from odoo import SUPERUSER_ID, api, models
from odoo.db.errors import PG_RETRY_EXCEPTIONS

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _consume_api_scope_budget(cls, scope, uid):
        """A scope's budget is a token bucket per key holder, kept on a cursor
        of its own so a refused call is still counted."""
        if not scope.budget_requests:
            return
        try:
            with scope.env.registry.cursor() as cr:
                allowed = (
                    api.Environment(cr, SUPERUSER_ID, {})["rate.limit.bucket"]
                    .sudo()
                    .consume_for_key(
                        f"api_scope:{scope.id}:user:{uid}",
                        subject_model="res.users.apikeys.scope",
                        subject_id=scope.id,
                        capacity=scope.budget_requests,
                        window_seconds=scope.budget_window_seconds,
                    )
                )
        except PG_RETRY_EXCEPTIONS:
            raise
        except Exception:
            _logger.exception(
                "Budget bookkeeping failed for scope %s; allowing the call", scope.key
            )
            return
        if not allowed:
            raise TooManyRequests(
                f"The API key's scope '{scope.key}' allows "
                f"{scope.budget_requests} calls per "
                f"{scope.budget_window_seconds} seconds."
            )
