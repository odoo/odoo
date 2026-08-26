# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Domain


class ProductPricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['product.pricelist', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        pricelist_ids = [preset['pricelist_id'] for preset in data['pos.preset']]
        all_ids = config._get_available_pricelists().ids + pricelist_ids
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
    def _load_pos_data_domain(self, data, config):
        pricelist_ids = [p['id'] for p in data['product.pricelist']]
        domain = [('pricelist_id', 'in', pricelist_ids)]

        if not self._last_server_date_to_load():
            product_tmpl_ids = [p['product_tmpl_id'] for p in data['product.product']]
            product_ids = [p['id'] for p in data['product.product']]
            now = fields.Datetime.now()
            domain += [
                '|', ('product_tmpl_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
                '|', ('product_id', '=', False), ('product_id', 'in', product_ids),
                '|', ('date_start', '=', False), ('date_start', '<=', now),
                '|', ('date_end', '=', False), ('date_end', '>', now),
            ]
        return domain

    @api.model
    def _server_date_to_domain(self, domain):
        if last_server_date := self._last_server_date_to_load():
            now = fields.Datetime.now()
            domain = Domain.AND([
                domain,
                Domain.OR([
                    [('write_date', '>', last_server_date)],
                    ['&', ('date_start', '>', last_server_date), ('date_start', '<=', now)],
                ]),
            ])
        return domain

    @api.model
    def _load_pos_data_fields(self, config):
        return ['product_tmpl_id', 'product_id', 'pricelist_id', 'price_surcharge', 'price_discount', 'price_round',
                'price_min_margin', 'price_max_margin', 'company_id', 'currency_id', 'date_start', 'date_end', 'compute_price',
                'fixed_price', 'percent_price', 'base_pricelist_id', 'base', 'categ_id', 'min_quantity', 'uom_id']
