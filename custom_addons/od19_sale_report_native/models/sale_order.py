# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Values backing the native (QWeb) Sale Order print forms.

The legacy Jasper form (``F-S-002`` / ``dtr_sales_form``) prints an amount block
that Odoo 19 does not expose out of the box: the gross amount *before* the line
(trade) discount and the trade discount itself.  It also needs a couple of
counters for the improved layout.  They are all computed here so both report
variants show exactly the same figures as the Jasper original.
"""
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_amount_gross = fields.Monetary(
        string="Gross Amount (Before Trade Discount)",
        compute="_compute_od19_report_values",
        currency_field="currency_id",
        help="Quantity x unit price of every product line, before the line "
        "(trade) discount is applied.",
    )
    od19_amount_trade_discount = fields.Monetary(
        string="Trade Discount Amount",
        compute="_compute_od19_report_values",
        currency_field="currency_id",
        help="Difference between the gross amount and the untaxed amount, i.e. "
        "the total of the line discounts.",
    )
    od19_report_line_count = fields.Integer(
        string="Printed Line Count",
        compute="_compute_od19_report_values",
        help="Number of product lines printed on the sale order form.",
    )
    od19_report_total_qty = fields.Float(
        string="Printed Total Quantity",
        compute="_compute_od19_report_values",
        help="Total quantity of every product line printed on the form.",
    )

    @api.depends(
        "order_line.product_uom_qty",
        "order_line.price_unit",
        "order_line.display_type",
        "amount_untaxed",
    )
    def _compute_od19_report_values(self):
        for order in self:
            product_lines = order.order_line.filtered(
                lambda line: not line.display_type
            )
            gross = sum(
                line.product_uom_qty * line.price_unit for line in product_lines
            )
            order.od19_amount_gross = gross
            order.od19_amount_trade_discount = gross - order.amount_untaxed
            order.od19_report_line_count = len(product_lines)
            order.od19_report_total_qty = sum(
                product_lines.mapped("product_uom_qty")
            )

    def od19_amount_in_words(self, lang=None):
        """Return the grand total written in words (``lang`` = res.lang code)."""
        self.ensure_one()
        currency = self.currency_id.with_context(lang=lang or self.env.user.lang)
        return currency.amount_to_text(self.amount_total)

    def od19_tax_labels(self):
        """Return the distinct tax labels applied on the product lines."""
        self.ensure_one()
        labels = []
        for tax in self.order_line.filtered(
            lambda line: not line.display_type
        ).tax_ids:
            if tax.name not in labels:
                labels.append(tax.name)
        return labels
