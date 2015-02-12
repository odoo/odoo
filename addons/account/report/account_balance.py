# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, api
from openerp.tools.translate import _
from common_report_header import common_report_header

class AccountBalanceReport(models.AbstractModel, common_report_header):
    _name = 'report.account.report_trialbalance'

    @api.model
    def _lines(self, form, ids=None, done=None):
        def _process_child(accounts, disp_acc, parent):
            account_recs = [acct for acct in accounts if acct.id == parent]
            for account_rec in account_recs:
                res = {
                    'id': account_rec.id,
                    'type': account_rec.type,
                    'code': account_rec.code,
                    'name': account_rec.name,
                    'level': account_rec.level,
                    'debit': account_rec.debit,
                    'credit': account_rec.credit,
                    'balance': account_rec.balance,
                    'parent_id': account_rec.parent_id,
                    'bal_type': '',
                }
                self.sum_debit += account_rec['debit']
                self.sum_credit += account_rec['credit']
                currency = acc_id.currency_id and acc_id.currency_id or acc_id.company_id.currency_id
                if disp_acc == 'movement':
                    if not currency.is_zero(res['credit']) or not currency.is_zero(res['debit']) or not currency.is_zero(res['balance']):
                        self.result_acc.append(res)
                elif disp_acc == 'not_zero':
                    if not currency.is_zero(res['balance']):
                        self.result_acc.append(res)
                else:
                    self.result_acc.append(res)
                if account_rec['child_id']:
                    for child in account_rec['child_id']:
                        _process_child(accounts, disp_acc, child)

        obj_account = self.env['account.account']
        if not ids:
            ids = form.get('ids', [])
        if not ids:
            return []
        if not done:
            done={}
        ctx = self._context.copy()
        ctx['fiscalyear'] = form['fiscalyear_id']
        if form['filter'] == 'filter_date':
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']
        ctx['state'] = form['target_move']
        parents = ids
        child_ids = obj_account.with_context(ctx).browse(ids)._get_children_and_consol()
        if child_ids:
            ids = child_ids
        accounts = obj_account.browse(ids)

        for parent in parents:
            if parent in done:
                continue
            done[parent] = 1
            _process_child(accounts, form['display_account'], parent)
        return self.result_acc

    @api.model
    def _get_display_account(self, data):
        if data.get('form', False) and data['form'].get('display_account', False) == 'all':
            return _('All accounts')
        elif data.get('form', False) and data['form'].get('display_account', False) == 'movement':
            return _('With movements')
        elif data.get('form', False) and data['form'].get('display_account', False) == 'not_zero':
            return _('With balance not equal to zero')
        return ''

    @api.multi
    def render_html(self, data=None):
        self.sum_debit = 0.00
        self.sum_credit = 0.00
        self.result_acc = []
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('account.report_trialbalance')
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self,
            'data': data,
            'get_account': self._get_account,
            'get_fiscalyear': self._get_fiscalyear,
            'get_display_account': self._get_display_account,
            'get_target_move': self._get_target_move,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'lines': self._lines
        }
        return report_obj.render('account.report_trialbalance', docargs)

