# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountTaxReport(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = 'account.tax.report'
    _description = 'Tax Report'

    options = fields.Selection([('accrual_basis', 'Accrual Basis Method'), ('cash_basis', 'Cash Basis Method')], default='accrual_basis', string='Options')

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['options'])[0])
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('account.action_report_account_tax').report_action(records, data=data)
