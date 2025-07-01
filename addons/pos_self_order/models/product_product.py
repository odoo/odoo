# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations
from typing import List, Dict
from odoo import api, models, fields
from odoo.osv.expression import AND


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    self_order_available = fields.Boolean(
        string="Available in Self Order",
        help="If this product is available in the Self Order screens",
        default=True,
    )

    @api.onchange('available_in_pos')
    def _on_change_available_in_pos(self):
        for record in self:
            if not record.available_in_pos:
                record.self_order_available = False

    def write(self, vals_list):
        if 'available_in_pos' in vals_list:
            if not vals_list['available_in_pos']:
                vals_list['self_order_available'] = False

        res = super().write(vals_list)

        if 'self_order_available' in vals_list:
            for record in self:
                for product in record.product_variant_ids:
                    product._send_availability_status()
        return res

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['self_order_available']
        return params

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        params = super()._load_pos_self_data_fields(config_id)
        params += ['public_description', 'list_price']
        return params
    
    @api.model
    def _load_pos_self_data_domain(self, data):
        domain = super()._load_pos_self_data_domain(data)
        return AND([domain, [('self_order_available', '=', True)]])

    def _load_pos_self_data(self, data):
        domain = self._load_pos_self_data_domain(data)
        config_id = data['pos.config']['data'][0]['id']

        # Add custom fields for 'formula' taxes.
        fields = set(self._load_pos_self_data_fields(config_id))
        taxes = self.env['account.tax'].search(self.env['account.tax']._load_pos_data_domain(data))
        product_fields = taxes._eval_taxes_computation_prepare_product_fields()
        fields = list(fields.union(product_fields))

        config = self.env['pos.config'].browse(config_id)
        products = self.with_context(display_default_code=False).search_read(
            domain,
            fields,
            limit=config.get_limited_product_count(),
            order='sequence,default_code,name',
            load=False
        )
        combo_products = self.browse((p['id'] for p in products if p["type"]=="combo"))
        combo_products_choice = self.with_context(display_default_code=False).search_read(
            [("id", 'in', combo_products.combo_ids.combo_item_ids.product_id.ids), ("id", "not in", [p['id'] for p in products])],
            fields,
            limit=config.get_limited_product_count(),
            order='sequence,default_code,name',
            load=False
        )
        products.extend(combo_products_choice)
        for product in products:
            product['image_128'] = bool(product['image_128'])

        data['pos.config']['data'][0]['_product_default_values'] = \
            self.env['account.tax']._eval_taxes_computation_prepare_product_default_values(product_fields)

        self._compute_product_price_with_pricelist(products, config_id)
        return {
            'data': products,
            'fields': fields,
        }

    def _compute_product_price_with_pricelist(self, products, config_id):
        config = self.env['pos.config'].browse(config_id)
        pricelist = config.pricelist_id

        product_ids = [product['id'] for product in products]
        product_objs = self.env['product.product'].browse(product_ids)

        product_map = {product.id: product for product in product_objs}
        loaded_product_tmpl_ids = list({p['product_tmpl_id'] for p in products})
        archived_combinations = self._get_archived_combinations_per_product_tmpl_id(loaded_product_tmpl_ids)

        for product in products:
            product_obj = product_map.get(product['id'])
            if product_obj:
                product['lst_price'] = pricelist._get_product_price(
                    product_obj, 1.0, currency=config.currency_id
                )
            if archived_combinations.get(product['product_tmpl_id']):
                product['_archived_combinations'] = archived_combinations[product['product_tmpl_id']]

    def _filter_applicable_attributes(self, attributes_by_ptal_id: Dict) -> List[Dict]:
        """
        The attributes_by_ptal_id is a dictionary that contains all the attributes that have
        [('create_variant', '=', 'no_variant')]
        This method filters out the attributes that are not applicable to the product in self
        """
        self.ensure_one()
        return [
            attributes_by_ptal_id[id]
            for id in self.attribute_line_ids.ids
            if attributes_by_ptal_id.get(id) is not None
        ]

    def write(self, vals_list):
        res = super().write(vals_list)
        if 'self_order_available' in vals_list:
            for record in self:
                record._send_availability_status()
        return res

    def _send_availability_status(self):
        config_self = self.env['pos.config'].sudo().search([('self_ordering_mode', '!=', 'nothing')])
        for config in config_self:
            if config.current_session_id and config.access_token:
                config._notify('PRODUCT_CHANGED', {
                    'product.product': self.read(self._load_pos_self_data_fields(config.id), load=False)
                })
