# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_deposit = fields.Boolean(help='This product is used as a deposit product.')
    deposit_product_id = fields.Many2one(
        'product.product',
        compute='_compute_deposit_product_id',
        inverse='_set_deposit_product_id',
        store=True,
        ui_domain="[('is_deposit', '=', True), ('available_in_pos', '=', True)]",
        help='The deposit product that is added when this product is sold.',
    )

    @api.depends('product_variant_ids.deposit_product_id')
    def _compute_deposit_product_id(self):
        self._compute_template_field_from_variant_field('deposit_product_id', multi_variant=True)

    def _set_deposit_product_id(self):
        self._set_product_variant_field('deposit_product_id', update_all_variants=True)

    def _get_related_fields_variant_template(self):
        return super()._get_related_fields_variant_template() + ['deposit_product_id']

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['is_deposit']

    def _load_pos_metadata(self, data, search_params={}):
        super()._load_pos_metadata(data, search_params)
        product_tmpls = data['product.template']['records']
        deposit_tmpls = product_tmpls.product_variant_ids.deposit_product_id.product_tmpl_id
        data['product.template']['records'] |= deposit_tmpls.filtered('available_in_pos')
        return data

    @api.constrains('is_deposit')
    def _check_is_deposit(self):
        deposit_tmpls = self.filtered('is_deposit')
        if deposit_tmpls.with_context(active_test=False).product_variant_ids.deposit_product_id:
            raise ValidationError(self.env._("A deposit product cannot have another deposit product."))
        if self.env['product.product'].with_context(active_test=False).search_count(
            [('deposit_product_id.product_tmpl_id', 'in', (self - deposit_tmpls).ids)], limit=1,
        ):
            raise ValidationError(self.env._("A product used as the deposit of another product must be a deposit product."))
