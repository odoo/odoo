# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        account_vals = super(AccountJournal, self)._prepare_liquidity_account(name, company, currency_id, type)

        if company.country_id.code == 'DK':
            # Ensure the newly liquidity accounts have the right account group in order to be part
            # of the Danish financial reports.
            xml_id = self.env.ref('l10n_dk.account_group_liquidity').id
            account_vals['group_id'] = xml_id

        return account_vals
