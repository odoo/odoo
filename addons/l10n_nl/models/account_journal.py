# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _fill_missing_values(self, vals):
        super()._fill_missing_values(vals)

        if vals.get('type') != 'purchase':
            return

        company = self.env['res.company'].browse(vals['company_id']) if vals.get('company_id') else self.env.company
        if company.country_id.code == "NL" and not vals.get('type_control_ids', [(6, 0, [])])[0][2]:
            type_control_ids = self.env.ref('account.data_account_type_direct_costs').ids
            vals['type_control_ids'] = [(6, 0, type_control_ids)]

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        # OVERRIDE
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)

        if company.account_fiscal_country_id.code == 'NL':
            # Ensure the newly liquidity accounts have the right account tag in order to be part
            # of the Dutch financial reports.
            account_vals.setdefault('tag_ids', [])
            account_vals['tag_ids'].append((4, self.env.ref('l10n_nl.account_tag_25').id))

        return account_vals
