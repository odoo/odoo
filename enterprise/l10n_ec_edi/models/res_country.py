# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class Country(models.Model):
    _inherit = 'res.country'

    # Columns
    l10n_ec_code_ats = fields.Char(
        string="ATS Code",
        size=3,
        help="Used in ecuador to describe the country code for the ATS. Up to 3 digits.",
    )
    l10n_ec_code_tax_haven = fields.Char(
        string="ATS Tax Haven Code",
        size=3,  # In the SRI's electronic documents specification, it mentions that the length of the field must be 3 digits
        help="Used in ecuador to describe a tax haven code for the ATS. Up to 3 digits.",
    )
