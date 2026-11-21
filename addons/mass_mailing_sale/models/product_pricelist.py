from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def mass_mailing_get_item_prices(self, product_id):
        self.ensure_one()
        product_id = self.env['product.product'].browse(product_id)
        product_id.ensure_one()
        current_price, rule_id = self._get_product_price_rule(product_id, 1, date=fields.Datetime.now())
        rule_id = self.env['product.pricelist.item'].browse(rule_id)
        price_before_discount = rule_id._compute_price_before_discount(
            product=product_id,
            quantity=1,
            uom=product_id._get_main_uom(),
            date=fields.Datetime.now(),
            currency=self.currency_id,
        )
        return {
            "price_before_discount": price_before_discount,
            "current_price": current_price,
            "currency_id": self.currency_id.id,
        }
