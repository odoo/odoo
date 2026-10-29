# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrdeLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_agent_ids(self):
        """Add salesman agent if configured so and no other commission
        already populated.
        """
        result = super()._compute_agent_ids()
        for record in self.filtered(lambda x: x.order_id.partner_id):
            partner = record.order_id.user_id.partner_id
            if not record.agent_ids and partner.agent and partner.salesman_as_agent:
                record.agent_ids = [(0, 0, record._prepare_agent_vals(partner))]
        return result
