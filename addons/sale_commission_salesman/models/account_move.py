# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_agent_ids(self):
        """Add salesman agent if configured so and no other commission
        already populated.
        """
        result = super()._compute_agent_ids()
        for record in self.filtered(
            lambda x: x.move_id.partner_id
            and x.move_id.move_type[:3] == "out"
            and x.product_id
            and not x.agent_ids
        ):
            partner = record.move_id.invoice_user_id.partner_id
            if partner.agent and partner.salesman_as_agent:
                record.agent_ids = [(0, 0, record._prepare_agent_vals(partner))]
        return result
