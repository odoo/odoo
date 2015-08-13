# -*- coding: utf-8 -*-

import time

from openerp import api, models, _
from common_report_header import CommonReportHeader


class ReportTrialBalance(models.AbstractModel, CommonReportHeader):
    _name = 'report.account.report_trialbalance'

    @api.multi
    def _process(self, form):
        self.result_acc = []
        accounts = self.env['account.account'].search([])

        data = self.with_context(form.get('used_context'))._compute(accounts)
        for account in accounts:
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res = {
                'id': account.id,
                'internal_type': account.internal_type,
                'code': account.code,
                'name': account.name,
                'bal_type': '',
                'debit': data[account.id].get('debit'),
                'credit': data[account.id].get('credit'),
                'balance': data[account.id].get('balance'),
            }
            if form['display_account'] == 'movement':
                if not currency.is_zero(res['credit']) or not currency.is_zero(res['debit']) or not currency.is_zero(res['balance']):
                    self.result_acc.append(res)
            elif form['display_account'] == 'not_zero':
                if not currency.is_zero(res['balance']):
                    self.result_acc.append(res)
            else:
                self.result_acc.append(res)

    def lines(self, form):
        self._process(form)
        return self.result_acc


    @api.multi
    def render_html(self, data):
        self.model = self._context.get('active_model')
        docs = self.env[self.model].browse(self._context.get('active_id'))

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['options']['form'],
            'docs': docs,
            'time': time,
            'lines': self.lines,
            'get_target_move': self._get_target_move,
        }
        return self.env['report'].render('account.report_trialbalance', docargs)
