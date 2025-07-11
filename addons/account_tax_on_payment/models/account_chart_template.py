# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    default_account_advance_payment_tax_account_id = fields.Many2one('account.account.template', string="Advance Payment Tax Account")

    def _load_company_accounts(self, account_ref, company):
        res = super()._load_company_accounts(account_ref, company)
        if self.default_account_advance_payment_tax_account_id:
            company.write({
                'account_advance_payment_tax_account_id': account_ref.get(self.default_account_advance_payment_tax_account_id)
            })
        return res

    def _load(self, company):
        res = super()._load(company)
        miscellaneous_journal = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', company.id)], limit=1)
        company.write({
            'account_advance_payment_tax_adjustment_journal_id': miscellaneous_journal.id
        })
        return res
