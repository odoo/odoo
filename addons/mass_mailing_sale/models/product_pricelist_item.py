from odoo import fields, models
from odoo.fields import Domain


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def mass_mailing_get_item_prices(self, product_id):
        self.ensure_one()
        product_id = self.env['product.product'].browse(product_id)
        product_id.ensure_one()
        base_price = self._compute_base_price(product_id, 1, False, currency=self.currency_id)
        current_price = self._compute_price(product_id, 1, False, currency=self.currency_id)
        return {
            "base_price": base_price,
            "current_price": current_price,
            "currency_id": self.currency_id.id,
        }

    def mass_mailing_get_pricelist_domain(self, product_id):
        """
        As the builder has to do an ORM call to check for whether the pricelist feature is enabled anyways,
        we take the opportunity to use the preexisting applicable rules method to directly fetch the pricelist
        domain for our product.
        :return false if the pricelist feature is disabled, a domain otherwise
        """
        product_id = self.env['product.product'].search_fetch(
            [('id', '=', product_id)],
            ['product_tmpl_id', 'categ_id'],
        )
        product_id.ensure_one()  # raise if no product
        if not self.env['res.groups']._is_feature_enabled('product.group_product_pricelist'):
            return False

        date = fields.Date.context_today(self.env.user)
        templates_domain = Domain('product_tmpl_id', 'in', product_id.product_tmpl_id.ids)
        products_domain = Domain('product_id', 'in', product_id.ids)

        return Domain.AND([
            Domain('categ_id', '=', False) | Domain('categ_id', 'parent_of', product_id.categ_id.ids),
            Domain('product_tmpl_id', '=', False) | templates_domain,
            Domain('product_id', '=', False) | products_domain,
            Domain('date_start', '=', False) | Domain('date_start', '<=', date),
            Domain('date_end', '=', False) | Domain('date_end', '>=', date),
        ])
