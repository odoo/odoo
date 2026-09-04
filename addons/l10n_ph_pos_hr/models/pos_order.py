# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_ph_pending_audit_actions = fields.Json(
        string="Pending PH Audit Actions",
        default=list,
        copy=False,
        help="Offline audit actions attached to the order and replayed on backend sync.",
    )

    def _l10n_ph_process_pending_audit_actions(self):
        """Replay offline audit actions that were queued on the order during POS sync."""
        for order in self:
            pending_actions = order.l10n_ph_pending_audit_actions
            if not pending_actions:
                continue
            remaining = []
            for action in pending_actions:
                action.setdefault("action_type", "line_void")
                try:
                    order.session_id.sudo().l10n_ph_log_order_line_action(action)
                except Exception:
                    remaining.append(action)
                    _logger.exception(
                        "l10n_ph_pos: failed to replay pending audit action %s for order %s",
                        action.get("action_uid"),
                        order.id,
                    )
            if len(remaining) != len(pending_actions):
                order.sudo().write(
                    {"l10n_ph_pending_audit_actions": remaining or False},
                )

    @api.model
    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        self.browse(order_id)._l10n_ph_process_pending_audit_actions()
        return order_id
