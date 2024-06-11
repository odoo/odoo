# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_cl_sii_code = fields.Integer('SII Code', group_operator=False)
