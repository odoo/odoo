# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ec_code_base = fields.Char(
        string="Code base",
        help="Ecuador: Tax declaration code of the base amount prior to the calculation of the tax.",
    )
    l10n_ec_code_applied = fields.Char(
        string="Code applied",
        help="Ecuador: Tax declaration code of the resulting amount after the calculation of the tax.",
    )
    l10n_ec_code_ats = fields.Char(
        string="Code ATS",
        help="Ecuador: Indicates if the purchase invoice supports tax credit or cost or expenses, conforming table 5 of ATS.",
    )
