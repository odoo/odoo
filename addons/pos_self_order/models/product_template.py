from odoo import models, fields, api
from odoo.fields import Domain


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    self_order_available = fields.Boolean(
        string="Available in Self Order",
        help="If this product is available in the Self Order screens",
        default=True,
    )

    self_order_visible = fields.Boolean(compute='_compute_self_order_visible')

    @api.model
    def _load_pos_self_data_read(self, records, config):
        fields = set(self._load_pos_self_data_fields(config))
        products = records.sorted('is_favorite DESC,pos_sequence,name').read(fields, load=False)
        self._process_pos_self_ui_products(products)
        for product in products:
            product['_is_pos_special_product'] = product['id'] in config._get_special_products().ids

        return products

    def _process_pos_self_ui_products(self, products):
        self._add_archived_combinations(products)
        for product in products:
            product['image_128'] = bool(product['image_128'])

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['self_order_available']
        return params

    @api.model
    def _load_pos_self_data_domain(self, data):
        domain = super()._load_pos_self_data_domain(data)
        domain = Domain.AND([domain, [('self_order_available', '=', True)]])
        # Also include templates for delivery products referenced by active presets
        delivery_tmpl_ids = data['pos.preset'].delivery_product_id.product_tmpl_id
        if delivery_tmpl_ids:
            domain = Domain.OR([domain, [('id', 'in', delivery_tmpl_ids.ids)]])
        return domain

    @api.onchange('available_in_pos')
    def _on_change_available_in_pos(self):
        for record in self:
            if not record.available_in_pos:
                record.self_order_available = False

    def _compute_self_order_visible(self):
        active_self_order_configs = self.env['pos.config'].sudo().search_count([('self_ordering_mode', '!=', 'nothing')])
        for product in self:
            product.self_order_visible = bool(active_self_order_configs)

    def write(self, vals):
        if 'available_in_pos' in vals:
            if not vals['available_in_pos']:
                vals['self_order_available'] = False

        res = super().write(vals)

        if 'self_order_available' in vals:
            for record in self:
                for product in record.product_variant_ids:
                    product._send_availability_status()
        return res

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_512", "image_128"] and self.sudo().self_order_available:
            return True
        return super()._can_return_content(field_name, access_token)

    @api.model
    def _load_pos_self_metadata(self, data, search_params={}):
        super()._load_pos_self_metadata(data, search_params)
        old_data = data['product.template']
        self._load_pos_metadata(data, search_params)
        products = data['product.template']['records']
        combo_products = products.combo_ids.combo_item_ids.product_id.product_tmpl_id
        additional_products = (combo_products + products.pos_optional_product_ids).filtered_domain([
            ('self_order_available', '=', True),
        ])
        presets = self.env['pos.preset'].sudo().search([
            '|',
            ('delivery_product_id', '!=', False),
            ('service_fee_product_id', '!=', False),
        ])
        preset_product_tmpls = (
            presets.delivery_product_id.product_tmpl_id
            | presets.service_fee_product_id.product_tmpl_id
        )
        all_products = products | additional_products | preset_product_tmpls

        if data['pos.config']['records'].tip_product_id:
            all_products |= data['pos.config']['records'].tip_product_id.product_tmpl_id

        data['product.template'] = {
            **old_data,
            'records': all_products,
        }
        return data
