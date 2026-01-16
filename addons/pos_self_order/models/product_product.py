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

    @api.depends('pos_categ_ids', 'pos_categ_ids.pos_config_ids.self_ordering_mode')
    def _compute_self_order_visible(self):
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
        if field_name == "image_512" and self.sudo().self_order_available:
            return True
        return super()._can_return_content(field_name, access_token)


class ProductProduct(models.Model):
    _inherit = "product.product"

<<<<<<< 1b67b6b62859ef706b63a1ef34393013bf96d39e
||||||| 4dd7bf0020def9ccdb05ec6ae3862616122b84df
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

=======
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

        archived_combinations = self._get_archived_combinations_per_product_tmpl_id(
            list({p['product_tmpl_id'] for p in products})
        )
        lst_prices = config.pricelist_id._get_products_price(
            self.env['product.product'].browse([product['id'] for product in products]),
            quantity=1.0,
            currency=config.currency_id,
        )

        for product in products:
            if product['id'] in lst_prices:
                product['lst_price'] = lst_prices[product['id']]
            if archived_combination := archived_combinations.get(product['product_tmpl_id']):
                product['_archived_combinations'] = archived_combination

>>>>>>> edb21093f7c5c38191302b1ab2f71157ac55687e
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
        if field_name == "image_512" and self.sudo().self_order_available:
            return True
        return super()._can_return_content(field_name, access_token)
