# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_ph_accumulated_counted = fields.Boolean(
        string="Counted in PH Accumulated Total",
        copy=False,
        readonly=True,
        help="Whether this order has been included in the accumulated total sales counter.",
    )
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
        synced_order = self.browse(order_id)
        synced_order._l10n_ph_process_pending_audit_actions()
        synced_order._l10n_ph_accumulate_sales()
        return order_id

    def _l10n_ph_accumulate_sales(self):
        """Accumulate sales totals for eligible (paid) orders not yet counted."""
        to_count = self.filtered(
            lambda o: (
                o.state in ("paid", "done", "invoiced")
                and o.config_id
                and not o.l10n_ph_accumulated_counted
            ),
        )
        if not to_count:
            return
        self.env["pos.config"]._l10n_ph_add_accumulated_total_sales(
            to_count._l10n_ph_claim_orders_for_accumulated_sales(),
        )

    def _l10n_ph_claim_orders_for_accumulated_sales(self):
        self.env.cr.execute(
            SQL(
                """
             UPDATE pos_order AS po
                SET l10n_ph_accumulated_counted = TRUE
              WHERE id = ANY(%s)
               AND l10n_ph_accumulated_counted IS NOT TRUE
            RETURNING COALESCE(
                          config_id,
                          (SELECT ps.config_id FROM pos_session AS ps WHERE ps.id = po.session_id)
                      ),
                      COALESCE(
                          NULLIF(amount_total, 0),
                          (SELECT COALESCE(SUM(pol.price_subtotal_incl), 0)
                             FROM pos_order_line AS pol WHERE pol.order_id = po.id)
                      )
            """,
                self.ids,
            ),
        )
        totals_by_config = defaultdict(float)
        for config_id, amount_total in self.env.cr.fetchall():
            if config_id:
                totals_by_config[config_id] += amount_total
        self.invalidate_recordset(["l10n_ph_accumulated_counted"])
        return totals_by_config

    def action_pos_order_paid(self):
        result = super().action_pos_order_paid()
        self._l10n_ph_accumulate_sales()
        return result
