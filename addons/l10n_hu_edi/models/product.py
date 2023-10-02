# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_hu_product_code_type = fields.Selection(
        [
            ("VTSZ", "VTSZ"),
            ("TESZOR", "TESZOR"),
            ("KN", "KN"),
            ("AHK", "AHK"),
            ("KT", "KT"),
            ("CSK", "CSK"),
            ("EJ", "EJ"),
            ("OWN", "OWN"),
            ("OTHER", "OTHER"),
        ],
        string="Product Code Type",
    )
    l10n_hu_product_code = fields.Char("Product Code")
