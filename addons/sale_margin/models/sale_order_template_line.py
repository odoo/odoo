# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderTemplateLine(models.Model):
    _inherit = "sale.order.template.line"

    purchase_price = fields.Float(
        string="Unit Cost", min_display_digits="Product Price", copy=False
    )

    def _prepare_order_line_values(self, fiscal_position, currency):
        vals = super()._prepare_order_line_values(fiscal_position, currency)
        if not self.product_id:
            vals["currency_id"] = self.sale_order_template_id.currency_id._convert(
                from_amount=self.purchase_price, to_currency=currency
            )

        return vals
