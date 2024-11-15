# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations
from typing import List, Dict
from odoo import api, models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    self_order_available = fields.Boolean(
        string="Available in Self Order",
        help="If this product is available in the Self Order screens",
        default=True,
    )

    def _load_pos_self_data(self, data):
        domain = self._load_pos_data_domain(data)

        # Add custom fields for 'formula' taxes.
        fields = set(self._load_pos_self_data_fields(data['pos.config'][0]['id']))
        taxes = self.env['account.tax'].search(self.env['account.tax']._load_pos_data_domain(data))
        product_fields = taxes._eval_taxes_computation_prepare_product_fields()
        fields = list(fields.union(product_fields))

        config = self.env['pos.config'].browse(data['pos.config'][0]['id'])
        products = self.search_read(
            domain,
            fields,
            limit=config.get_limited_product_count(),
            order='sequence,default_code,name',
            load=False
        )

        data['pos.config'][0]['_product_default_values'] = \
            self.env['account.tax']._eval_taxes_computation_prepare_product_default_values(product_fields)
        self._process_pos_self_ui_products(products)

        return products

    def _process_pos_self_ui_products(self, products):
        for product in products:
            product['_archived_combinations'] = []
            for product_product in self.env['product.product'].with_context(active_test=False).search([('product_tmpl_id', '=', product['id']), ('active', '=', False)]):
                product['_archived_combinations'].append(product_product.product_template_attribute_value_ids.ids)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['self_order_available']
        return params

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

    def _can_return_content(self, field_name=None, access_token=None):
        if self.self_order_available and field_name in ["image_128", "image_512"]:
            return True
        return super()._can_return_content(field_name, access_token)
