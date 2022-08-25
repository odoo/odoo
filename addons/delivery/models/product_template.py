# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hs_code = fields.Char(
        string="HS Code",
        help="Standardized code for international shipping and goods declaration. At the moment, only used for the FedEx shipping provider.",
    )
    country_of_origin = fields.Many2one(
        'res.country',
        'Origin of Goods',
        help="Rules of origin determine where goods originate, i.e. not where they have been shipped from, but where they have been produced or manufactured.\n"
             "As such, the ‘origin’ is the 'economic nationality' of goods traded in commerce.",
    )
