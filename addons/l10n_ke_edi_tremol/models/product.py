# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_ke_hsn_code = fields.Char(
        string='HSN code',
        help="Product code needed in case of not 16%. ",
    )
    l10n_ke_hsn_name = fields.Char(
        string='HSN description',
        help="Product code description needed in case of not 16%. ",
    )

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
