from odoo import api, fields, models

from .product_product import L10N_AE_GOODS_SERVICE_TYPE_SELECTION


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_ae_is_good_and_service = fields.Boolean(
        string='Is Good and Service',
        compute='_compute_l10n_ae_is_good_and_service',
        inverse='_set_l10n_ae_is_good_and_service',
    )
    l10n_ae_goods_service_type = fields.Selection(
        string='Goods and Service Type',
        compute='_compute_l10n_ae_goods_service_type',
        inverse='_set_l10n_ae_goods_service_type',
        selection=L10N_AE_GOODS_SERVICE_TYPE_SELECTION,
    )
    l10n_ae_classification_code = fields.Char(
        string='HS / Service Accounting Code',
        compute='_compute_l10n_ae_classification_code',
        inverse='_set_l10n_ae_classification_code',
    )

    @api.depends('product_variant_ids.l10n_ae_is_good_and_service')
    def _compute_l10n_ae_is_good_and_service(self):
        self._compute_template_field_from_variant_field('l10n_ae_is_good_and_service')

    def _set_l10n_ae_is_good_and_service(self):
        self._set_product_variant_field('l10n_ae_is_good_and_service')

    @api.depends('product_variant_ids.l10n_ae_goods_service_type')
    def _compute_l10n_ae_goods_service_type(self):
        self._compute_template_field_from_variant_field('l10n_ae_goods_service_type')

    def _set_l10n_ae_goods_service_type(self):
        self._set_product_variant_field('l10n_ae_goods_service_type')

    @api.depends('product_variant_ids.l10n_ae_classification_code')
    def _compute_l10n_ae_classification_code(self):
        self._compute_template_field_from_variant_field('l10n_ae_classification_code')

    def _set_l10n_ae_classification_code(self):
        self._set_product_variant_field('l10n_ae_classification_code')
