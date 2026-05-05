# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    def _get_extra_price(self, currency):
        self.ensure_one()
        if not self.show_price_extra:
            return 0.0

        if not self.price_extra:
            return 0.0

        price_extra = self.price_extra
        if not price_extra:
            return price_extra

        product_template = self.product_tmpl_id
        if currency != product_template.currency_id:
            price_extra = self.currency_id._convert(from_amount=price_extra, to_currency=currency)

        return self.product_tmpl_id._apply_taxes_to_price(price_extra, currency)
