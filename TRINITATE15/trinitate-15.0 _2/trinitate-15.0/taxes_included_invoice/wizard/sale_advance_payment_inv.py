# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th)

from odoo import fields, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    taxes_included = fields.Boolean(default=True)

    def _prepare_invoice_values(self, order, name, amount, so_line):
        res = super()._prepare_invoice_values(order, name, amount, so_line)
        tax_amount = so_line.tax_id.amount
        advance_with_tax = amount / ((tax_amount / 100) + 1)
        res["invoice_line_ids"][0][2].update({"price_unit": round(advance_with_tax, 2)})
        return res
