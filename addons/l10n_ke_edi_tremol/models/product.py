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
