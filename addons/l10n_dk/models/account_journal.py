# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


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
            account_vals['tag_ids'].append((4, self.env.ref('l10n_dk.account_tag_liquidity').id))

        return account_vals

    def create(self, vals_list):
        # EXTENDS account
        journals = super().create(vals_list)
        for journal in journals:
            if journal.type in ('sale', 'purchase') and journal.country_code == 'DK':
                # For Denmark we force hashing the entries for sales and purchase journals.
                journal.restrict_mode_hash_table = True
        return journals

    def write(self, vals):
        # EXTENDS account
        if 'restrict_mode_hash_table' in vals and not vals['restrict_mode_hash_table']:
            for journal in self:
                if journal.country_code == 'DK' and journal.type in ('sale', 'purchase'):
                    # For Denmark we force hashing the entries for sales and purchase journals.
                    del vals['restrict_mode_hash_table']
                    break
        res = super().write(vals)
        return res
