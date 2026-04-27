# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ro_saft_tax_type_id = fields.Many2one(
        comodel_name='l10n_ro_saft.tax.type',
        string='Romanian SAF-T Tax Type',
        help='A 3-digit number defined by ANAF to identify a type of tax in the D.406 export '
             '(e.g. 300 for VAT, 150 for withholding taxes on dividends...)',
    )
    l10n_ro_saft_tax_code = fields.Char(
        string='Romanian SAF-T Tax Code',
        help='A 6-digit number defined by ANAF to precisely identify taxes in the D.406 export '
             '(e.g. 310309 for domestic 19% VAT)',
        size=6,
    )
