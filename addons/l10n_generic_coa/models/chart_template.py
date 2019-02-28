# -*- coding: utf-8 -*-

from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
    def _create_bank_journals(self, company, acc_template_ref):
        '''
        When system automatically creates journals of bank and cash type when CoA is being installed
        do not enable the `Check` payment method on bank journals of type `Cash`.

        '''
        bank_journals = super(AccountChartTemplate, self)._create_bank_journals(company, acc_template_ref)
        profit_account = self.env['account.account'].search([('code', '=like', '202%')], limit=1)
        loss_account = self.env['account.account'].search([('code', '=like', '212%')], limit=1)
        bank_journals.filtered(lambda journal: journal.type == 'cash').write({
             'profit_account_id': profit_account.id,
             'loss_account_id': loss_account.id,
        })
        return bank_journals
