# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    l10n_cl_sii_code = fields.Integer(
        'SII Code'
    )


class AccountTaxTemplate(models.Model):
    _name = 'account.tax.template'
    _inherit = 'account.tax.template'

    l10n_cl_sii_code = fields.Integer(
        'SII Code'
    )
