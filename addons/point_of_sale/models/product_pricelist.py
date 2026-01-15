# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProductPricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['product.pricelist', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        pricelist_ids = [preset['pricelist_id'] for preset in data['pos.preset']]
        return [('id', 'in', config._get_available_pricelists().ids + pricelist_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'display_name', 'item_ids']


class ProductPricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        product_tmpl_ids = [p['product_tmpl_id'] for p in data['product.product']]
        product_ids = [p['id'] for p in data['product.product']]
        product_categ = [c['id'] for c in data['product.category']]
        pricelist_ids = [p['id'] for p in data['product.pricelist']]
        now = fields.Datetime.now()
        return [
            ('pricelist_id', 'in', pricelist_ids),
            '|', ('product_tmpl_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            '|', ('product_id', '=', False), ('product_id', 'in', product_ids),
            '|', ('date_start', '=', False), ('date_start', '<=', now),
            '|', ('date_end', '=', False), ('date_end', '>=', now),
            '|', ('categ_id', '=', False), ('categ_id', 'in', product_categ),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['product_tmpl_id', 'product_id', 'pricelist_id', 'price_surcharge', 'price_discount', 'price_round',
                'price_min_margin', 'price_max_margin', 'company_id', 'currency_id', 'date_start', 'date_end', 'compute_price',
                'fixed_price', 'percent_price', 'base_pricelist_id', 'base', 'categ_id', 'min_quantity']
