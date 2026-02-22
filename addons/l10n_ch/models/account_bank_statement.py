# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.addons.l10n_ch.models.res_bank import _is_l10n_ch_postal


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    def _find_or_create_bank_account(self):
        if self.company_id.account_fiscal_country_id.code in ('CH', 'LI') and _is_l10n_ch_postal(self.account_number):
            return self.env['res.partner.bank']._find_or_create_bank_account(
                account_number=self.account_number + " " + self.partner_id.name,
                partner=self.partner_id,
                company_id=self.company_id,
                extra_create_vals={'company_id': self.company_id},
            )
        return super()._find_or_create_bank_account()
