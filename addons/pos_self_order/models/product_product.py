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

    self_order_visible = fields.Boolean(
        compute='_compute_self_order_visible',
        store=True
    )

    def _load_pos_self_data(self, data):
        domain = self._load_pos_self_data_domain(data)
        fields = set(self._load_pos_self_data_fields(data['pos.config'][0]['id']))
        config = self.env['pos.config'].browse(data['pos.config'][0]['id'])
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

    def _post_read_pos_self_data(self, data):
        self._process_pos_self_ui_products(data)
        return super()._post_read_pos_self_data(data)

    def _process_pos_self_ui_products(self, products):
        self._add_archived_combinations(products)
        for product in products:
            product['image_128'] = bool(product['image_128'])

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['self_order_available']
        return params

    @api.model
    def _load_pos_self_data_domain(self, data):
        domain = super()._load_pos_self_data_domain(data)
        return AND([domain, [('self_order_available', '=', True)]])

    @api.onchange('available_in_pos')
    def _on_change_available_in_pos(self):
        for record in self:
            if not record.available_in_pos:
                record.self_order_available = False

    @api.depends('pos_categ_ids', 'pos_categ_ids.pos_config_ids.self_ordering_mode', 'pos_categ_ids.pos_config_ids.iface_available_categ_ids')
    def _compute_self_order_visible(self):
        if self.env['pos.config'].search_count([('self_ordering_mode', '!=', 'nothing'), ('limit_categories', '=', False)]):
            self.self_order_visible = True
        else:
            config_with_self = self.env['pos.config'].search([('self_ordering_mode', '!=', 'nothing')])
            categ_ids = config_with_self.iface_available_categ_ids.ids
            for product in self:
                product.self_order_visible = any(p_cat_id in categ_ids for p_cat_id in product.pos_categ_ids.ids)

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
                records = self.env["product.template"].load_product_from_pos(config.id, [('id', '=', self.product_tmpl_id.id)])
                payload = {}
                self_models = self.env["pos.config"]._load_self_data_models()
                for model in records:
                    if model in self_models:
                        payload[model] = records[model]
                config._notify('PRODUCT_CHANGED', payload)

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name == "image_512" and self.sudo().self_order_available:
            return True
        return super()._can_return_content(field_name, access_token)
