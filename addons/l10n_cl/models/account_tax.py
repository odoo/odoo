# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import account


class AccountTax(account.AccountTax):

    l10n_cl_sii_code = fields.Integer('SII Code', aggregator=False)
