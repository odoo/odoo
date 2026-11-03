# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_ph_accumulated_counted = fields.Boolean(
        string="Counted in PH Accumulated Total",
        copy=False,
        readonly=True,
        help="Whether this order has been included in the accumulated total sales counter.",
    )

    @api.model
    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        self.browse(order_id)._l10n_ph_accumulate_sales()
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
        totals_by_config = defaultdict(float)
        for order in self:
            config = order.config_id or order.session_id.config_id
            if not config:
                continue
            totals_by_config[config.id] += order.amount_total or sum(
                order.lines.mapped("price_subtotal_incl"),
            )
        self.write({"l10n_ph_accumulated_counted": True})
        return totals_by_config

    def action_pos_order_paid(self):
        result = super().action_pos_order_paid()
        self._l10n_ph_accumulate_sales()
        return result
