# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models


class ProductPricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['product.pricelist', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        pricelist_ids = data['pos.preset'].pricelist_id.ids
        all_ids = data['pos.config']._get_available_pricelists().ids + pricelist_ids
        referenced_base_pricelist_ids = self.env['product.pricelist.item'].search([
            ('pricelist_id', 'in', all_ids),
            ('base', '=', 'pricelist'),
            ('base_pricelist_id', '!=', False),
        ]).base_pricelist_id.ids
        return [('id', 'in', list(set(all_ids + referenced_base_pricelist_ids)))]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'display_name', 'currency_id', 'item_ids']

    @api.model
    def _load_pos_data_read(self, records, config):
        # Bypass the item_ids field: its dotted active domain forces a slow
        # ir.rule subquery. Search pricelist_id directly instead (indexed, no join).
        fields_to_read = [name for name in self._load_pos_data_fields(config) if name != 'item_ids']
        read_records = records._filtered_access("read").read(fields_to_read, load=False)

        items = self.env['product.pricelist.item'].search([('pricelist_id', 'in', records.ids)])
        item_ids_by_pricelist = defaultdict(list)
        for item in items:
            item_ids_by_pricelist[item.pricelist_id.id].append(item.id)
        for record in read_records:
            record['item_ids'] = item_ids_by_pricelist[record['id']]

        return read_records or []


class ProductPricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        pricelist_ids = data['product.pricelist'].ids
        product_tmpl_ids = data['product.product'].product_tmpl_id.ids
        product_ids = data['product.product'].ids
        product_categ = data['product.category'].ids

        now = fields.Datetime.now()
        return [
            ('pricelist_id', 'in', pricelist_ids),
            '|', ('product_tmpl_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            '|', ('product_id', '=', False), ('product_id', 'in', product_ids),
            '|', ('categ_id', '=', False), ('categ_id', 'in', product_categ),
            '|', ('date_start', '=', False), ('date_start', '<=', now),
            '|', ('date_end', '=', False), ('date_end', '>', now),
        ]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.pricelist', 'product.product', 'product.category']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['product_tmpl_id', 'product_id', 'pricelist_id', 'price_surcharge', 'price_discount', 'price_round',
                'price_min_margin', 'price_max_margin', 'company_id', 'currency_id', 'date_start', 'date_end', 'compute_price',
                'fixed_price', 'base_pricelist_id', 'base', 'categ_id', 'min_quantity', 'uom_id']
