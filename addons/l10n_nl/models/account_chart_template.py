# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        # Add tag to 999999 account
        res = super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        if company.country_id.code == 'NL':
            account = self.env['account.account'].search([('code', '=', '999999'), ('company_id', '=', self.env.company.id)])
            if account:
                account.tag_ids = [(4, self.env.ref('l10n_nl.account_tag_12').id)]
        return res

    @api.model
    def _prepare_transfer_account_for_direct_creation(self, name, company):
        res = super(AccountChartTemplate, self)._prepare_transfer_account_for_direct_creation(name, company)
        if company.country_id.code == 'NL':
            xml_id = self.env.ref('l10n_nl.account_tag_25').id
            res.setdefault('tag_ids', [])
            res['tag_ids'].append((4, xml_id))
        return res
