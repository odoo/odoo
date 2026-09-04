# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Copyright 2020 Tecnativa - Pedro M. Baeza

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    sale_type_id = fields.Many2one(
        comodel_name="sale.order.type",
        string="Sale Type",
        compute="_compute_sale_type_id",
        store=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        ondelete="restrict",
        copy=True,
        precompute=True,
    )

    @api.depends("partner_id", "company_id")
    @api.depends_context("default_move_type", "active_model", "company")
    def _compute_sale_type_id(self):
        # If create invoice from sale order, sale type will not computed.
        if not self.env.context.get("default_move_type", False) or self.env.context.get(
            "active_model", False
        ) in ["sale.order", "sale.advance.payment.inv"]:
            return
        sale_type = self.env["sale.order.type"].browse()
        self.sale_type_id = sale_type
        for record in self:
            if record.move_type not in ["out_invoice", "out_refund"]:
                record.sale_type_id = sale_type
                continue
            else:
                record.sale_type_id = record._origin.sale_type_id
            if not record.partner_id:
                record.sale_type_id = self.env["sale.order.type"].search(
                    [("company_id", "in", [self.env.company.id, False])], limit=1
                )
            else:
                sale_type = (
                    record.partner_id.with_company(record.company_id).sale_type
                    or record.partner_id.commercial_partner_id.with_company(
                        record.company_id
                    ).sale_type
                )
                if sale_type:
                    record.sale_type_id = sale_type

    @api.depends("sale_type_id")
    def _compute_invoice_payment_term_id(self):
        res = super()._compute_invoice_payment_term_id()
        for move in self.filtered("sale_type_id.payment_term_id"):
            move.invoice_payment_term_id = move.sale_type_id.payment_term_id
        return res

    @api.depends("sale_type_id")
    def _compute_journal_id(self):
        res = super()._compute_journal_id()
        for move in self.filtered("sale_type_id.journal_id"):
            move.journal_id = move.sale_type_id.journal_id
        return res
