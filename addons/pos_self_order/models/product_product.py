# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

from odoo import api, fields, models
from odoo.fields import Domain


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    self_order_available = fields.Boolean(
        string="Available in Self Order",
        help="If this product is available in the Self Order screens",
        default=True,
    )

    self_order_visible = fields.Boolean(compute='_compute_self_order_visible')

    def _load_pos_self_data_read(self, data, config):
        domain = self._load_pos_self_data_domain(data, config)
        fields = set(self._load_pos_self_data_fields(config))
        products = self.search_read(
            domain,
            fields,
            limit=config.get_limited_product_count(),
            order='sequence,default_code,name',
            load=False
        )

        combo_products = self.browse((p['id'] for p in products if p["type"] == "combo"))
        combo_products_choice = self.search_read(
            [("id", 'in', combo_products.combo_ids.combo_item_ids.product_id.product_tmpl_id.ids), ("id", "not in", [p['id'] for p in products])],
            fields,
            limit=config.get_limited_product_count(),
            order='sequence,default_code,name',
            load=False
        )
        products.extend(combo_products_choice)
        self._process_pos_self_ui_products(products)

        return products

    def _process_pos_self_ui_products(self, products):
        for product in products:
            product['_archived_combinations'] = []
            for product_product in self.env['product.product'].with_context(active_test=False).search([('product_tmpl_id', '=', product['id']), ('active', '=', False)]):
                product['_archived_combinations'].append(product_product.product_template_attribute_value_ids.ids)
            product['image_128'] = bool(product['image_128'])

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['self_order_available']
        return params

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        domain = super()._load_pos_self_data_domain(data, config)
        return Domain.AND([domain, [('self_order_available', '=', True)]])

    @api.onchange('available_in_pos')
    def _on_change_available_in_pos(self):
        for record in self:
            if not record.available_in_pos:
                record.self_order_available = False

    def _compute_self_order_visible(self):
        active_self_order_configs = self.env['pos.config'].sudo().search_count([('self_ordering_mode', '!=', 'nothing')])
        for product in self:
            product.self_order_visible = bool(active_self_order_configs)

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

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_512", "image_128"] and self.sudo().self_order_available:
            return True
        return super()._can_return_content(field_name, access_token)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _filter_applicable_attributes(self, attributes_by_ptal_id: dict) -> list[dict]:
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
                    'product.product': self.read(self._load_pos_self_data_fields(config), load=False)
                })

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name == "image_512" and self.sudo().self_order_available:
            return True
        return super()._can_return_content(field_name, access_token)
