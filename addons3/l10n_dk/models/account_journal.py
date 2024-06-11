# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        # OVERRIDE
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)

        if company.account_fiscal_country_id.code == 'DK':
            # Ensure the newly liquidity accounts have the right account tag in order to be part
            # of the Danish financial reports.
            account_vals.setdefault('tag_ids', [])
            if vals.get('type') == 'bank':
                account_vals['tag_ids'].append(Command.link(self.env.ref('l10n_dk.account_tag_6481').id))
            elif vals.get('type') == 'cash':
                account_vals['tag_ids'].append(Command.link(self.env.ref('l10n_dk.account_tag_6471').id))
            account_vals['tag_ids'].append(Command.link(self.env.ref('l10n_dk.account_tag_liquidity').id))

        return account_vals
