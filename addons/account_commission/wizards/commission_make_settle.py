# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# Copyright 2022 Quartile
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models


class CommissionMakeSettle(models.TransientModel):
    _inherit = "commission.make.settle"

    settlement_type = fields.Selection(
        selection_add=[("sale_invoice", "Sales Invoices")],
        ondelete={"sale_invoice": "cascade"},
    )

    def _get_account_settle_domain(self, agent, date_to_agent):
        return [
            ("invoice_date", "<", date_to_agent),
            ("agent_id", "=", agent.id),
            ("settled", "=", False),
            ("object_id.display_type", "=", "product"),
        ]

    def _get_agent_lines(self, agent, date_to_agent):
        """Filter sales invoice agent lines for this type of settlement."""
        if self.settlement_type != "sale_invoice":
            return super()._get_agent_lines(agent, date_to_agent)
        return self.env["account.invoice.line.agent"].search(
            self._get_account_settle_domain(agent, date_to_agent),
            order="invoice_date",
        )

    def _prepare_settlement_line_vals(self, settlement, line):
        """Prepare extra settlement values when the source is a sales invoice agent
        line.
        """
        res = super()._prepare_settlement_line_vals(settlement, line)
        if self.settlement_type == "sale_invoice":
            res.update(
                {
                    "invoice_agent_line_id": line.id,
                    "date": line.invoice_date,
                    "commission_id": line.commission_id.id,
                    "settled_amount": line.amount,
                }
            )
        return res
