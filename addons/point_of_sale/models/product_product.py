# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('product_tmpl_id', 'in', [p['id'] for p in data['product.template']])]

    @api.model
    def _load_pos_data_fields(self, config):
        taxes = self.env['account.tax'].search(self.env['account.tax']._check_company_domain(config.company_id.id))
        product_fields = taxes._eval_taxes_computation_prepare_product_fields()
        return list(product_fields.union({
            'id', 'lst_price', 'display_name', 'product_tmpl_id', 'product_template_variant_value_ids', 'currency_id',
            'product_template_attribute_value_ids', 'barcode', 'product_tag_ids', 'default_code', 'standard_price'
        }))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
            if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('product_tmpl_id.available_in_pos', '=', True)]):
                raise UserError(_(
                    "To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a hamburger from a customer’s hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!",
                ))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_special_product(self):
        self.product_tmpl_id._check_is_special_product()

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)

        different_currency = {}
        for product in read_records:
            currency_id = product['currency_id']
            if currency_id != config.currency_id.id:
                different_currency.setdefault(currency_id, []).append(product)

        for currency_id, products in different_currency.items():
            currency = self.env['res.currency'].browse(currency_id)
            for product in products:
                product['lst_price'] = currency._convert(
                    product['lst_price'], config.currency_id, self.env.company, fields.Date.today()
                )
                product['standard_price'] = currency._convert(
                    product['standard_price'], config.currency_id, self.env.company, fields.Date.today()
                )
        return read_records

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name == "image_128" and self.sudo().available_in_pos:
            return True
        return super()._can_return_content(field_name, access_token)

    def action_archive(self):
        self.product_tmpl_id._ensure_unused_in_pos()
        self.product_tmpl_id._check_is_special_product()
        return super().action_archive()
