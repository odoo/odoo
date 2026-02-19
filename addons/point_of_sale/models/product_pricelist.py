# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


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

    def _get_applicable_rules_domain(self, products, date, **kwargs):
        # Filter out subscription-rules targeting other products
        base_domain = super()._get_applicable_rules_domain(products, date, **kwargs)
        return Domain.AND([
            base_domain,
            ['|', ('pos_categ_id', '=', False), ('pos_categ_id', 'parent_of', products.pos_categ_ids.ids)]
        ])
