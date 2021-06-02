# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        account_vals = super(AccountJournal, self)._prepare_liquidity_account(name, company, currency_id, type)

        if company.country_id.code == 'DK':
            # Ensure the newly liquidity accounts have the right account tag in order to be part
            # of the Danish financial reports.
            xml_id = self.env.ref('l10n_dk.account_tag_liquidity').id
            account_vals['tag_ids'] = [(6, 0, [xml_id])]

        return account_vals
