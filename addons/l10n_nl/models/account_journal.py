# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        account_vals = super(AccountJournal, self)._prepare_liquidity_account(name, company, currency_id, type)

        # Ensure the newly liquidity accounts have the right account tag in order to be part
        # of the Dutch financial reports.
        tag_ids = account_vals.get('tag_ids', [])
        tag_ids.append((4, self.env.ref('l10n_nl.account_tag_25').id))
        account_vals['tag_ids'] = tag_ids

        return account_vals
