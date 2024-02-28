# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_in_pan = fields.Char(string="PAN", help="""PAN enables the department to link all transactions of the person with the department.
                                These transactions include taxpayments, TDS/TCS credits, returns of income/wealth/gift/FBT, specified transactions, correspondence, and so on.
                                thus, PAN acts as an identifier for the person with the tax department.""")

    @api.model
    def _commercial_fields(self):
        res = super()._commercial_fields()
        return res + ['l10n_in_pan']
