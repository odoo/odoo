# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def execute(self):
        # Add tag to 999999 account
        res = super(WizardMultiChartsAccounts, self).execute()
        account = self.env['account.account'].search([('code', '=', '999999'), ('company_id', '=', self.company_id.id)])
        if account:
            account.tag_ids = [(4, self.env.ref('l10n_nl.account_tag_12').id)]
        return res

    @api.model
    def _prepare_transfer_account(self, name, company):
        res = super(WizardMultiChartsAccounts, self)._prepare_transfer_account(name, company)
        xml_id = self.env.ref('l10n_nl.account_tag_25').id
        existing_tags = [x[-1:] for x in res.get('tag_ids', [])]
        res['tag_ids'] = [(6, 0, existing_tags + [xml_id])]
        return res
