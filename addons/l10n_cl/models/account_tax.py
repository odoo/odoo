# -*- coding: utf-8 -*-
from odoo.addons import account
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model, account.AccountTax):

    l10n_cl_sii_code = fields.Integer('SII Code', aggregator=False)
