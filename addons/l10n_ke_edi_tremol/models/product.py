# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_ke_hsn_code = fields.Char(
        string='KRA Item Code',
        help='Product code needed when not 16% VAT rated. ',
    )
    l10n_ke_hsn_name = fields.Char(
        string='KRA Item Description',
        help='Product code description needed when not 16% VAT rated. ',
    )
    current_country_code = fields.Char(compute='_compute_current_country_code')

    @api.depends_context('uid')
    def _compute_current_country_code(self):
        for product in self:
            product.current_country_code = self.env.company.country_id.code

class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_ke_hsn_code = fields.Char(
        string='HSN code',
        related='product_tmpl_id.l10n_ke_hsn_code',
        help="Product code needed in case of not 16%. ",
        readonly=False,
    )
    l10n_ke_hsn_name = fields.Char(
        string='HSN description',
        related='product_tmpl_id.l10n_ke_hsn_name',
        help="Product code description needed in case of not 16%. ",
        readonly=False,
    )
    current_country_code = fields.Char(compute='_compute_current_country_code')

    @api.depends_context('uid')
    def _compute_current_country_code(self):
        for product in self:
            product.current_country_code = self.env.company.country_id.code
