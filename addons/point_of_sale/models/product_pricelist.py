# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProductPricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['product.pricelist', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = data['pos.config']
        pricelist_ids = data['pos.preset'].pricelist_id.ids
        return [('id', 'in', config_id._get_available_pricelists().ids + pricelist_ids)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'display_name', 'item_ids']


class ProductPricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        product_tmpl_ids = data['product.product'].product_tmpl_id.ids
        product_ids = data['product.product'].ids
        product_categ = data['product.category'].ids
        pricelist_ids = data['product.pricelist'].ids

        today = fields.Date.today()
        return [
            ('pricelist_id', 'in', pricelist_ids),
            '|', ('product_tmpl_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            '|', ('product_id', '=', False), ('product_id', 'in', product_ids),
            '|', ('date_start', '=', False), ('date_start', '<=', today),
            '|', ('date_end', '=', False), ('date_end', '>=', today),
            '|', ('categ_id', '=', False), ('categ_id', 'in', product_categ),
        ]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.pricelist', 'product.product', 'product.category']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['product_tmpl_id', 'product_id', 'pricelist_id', 'price_surcharge', 'price_discount', 'price_round',
                'price_min_margin', 'price_max_margin', 'company_id', 'currency_id', 'date_start', 'date_end', 'compute_price',
                'fixed_price', 'percent_price', 'base_pricelist_id', 'base', 'categ_id', 'min_quantity']
