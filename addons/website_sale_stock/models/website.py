# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    def _get_product_available_qty(self, product, **kwargs):
        return product.with_context(warehouse_id=self.warehouse_id.id).free_qty

    def _get_json_ld_product(self, product_or_template):
        """ Override of `website_sale` to include availability of the product in the offer.
        """
        seo_data = super()._get_json_ld_product(product_or_template)
        if product_or_template.is_product_variant and product_or_template.is_storable:
            free_qty = self._get_product_available_qty(product_or_template.sudo())
            if free_qty or product_or_template.allow_out_of_stock_order:
                availability = 'https://schema.org/InStock'
            else:
                availability = 'https://schema.org/OutOfStock'
            seo_data['offers']['availability'] = availability
        return seo_data
