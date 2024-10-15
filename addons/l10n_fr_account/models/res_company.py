# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account, base_vat, l10n_fr


class ResCompany(base_vat.ResCompany, account.ResCompany, l10n_fr.ResCompany):

    l10n_fr_rounding_difference_loss_account_id = fields.Many2one('account.account', check_company=True)
    l10n_fr_rounding_difference_profit_account_id = fields.Many2one('account.account', check_company=True)
