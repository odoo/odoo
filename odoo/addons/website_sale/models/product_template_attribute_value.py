# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    def _get_extra_price(self, combination_info):
        self.ensure_one()
        if not self.price_extra:
            return 0.0

        price_extra = self.price_extra
        if not price_extra:
            return price_extra

        product_template = self.product_tmpl_id
        currency = combination_info['currency']
        if currency != product_template.currency_id:
            price_extra = self.currency_id._convert(
                from_amount=price_extra,
                to_currency=currency,
                company=self.env.company,
                date=combination_info['date'],
            )

        product_taxes = combination_info['product_taxes']
        if product_taxes:
            price_extra = self.env['product.template']._apply_taxes_to_price(
                price_extra,
                combination_info['currency'],
                product_taxes,
                combination_info['taxes'],
                self.product_tmpl_id,
            )

        return price_extra
