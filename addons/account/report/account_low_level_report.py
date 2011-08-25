##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import time

from report import report_sxw
from common_report_header import common_report_header
from tools.translate import _

class report_account_common(report_sxw.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context=None):
        super(report_account_common, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'get_lines': self.get_lines,

            'time': time,
#            'get_report_details': self._get_report_details,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_filter': self._get_filter,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
#            'get_account_details': self.get_account_details,
        })
        self.context = context

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
        return super(report_account_common, self).set_context(objects, data, new_ids, report_type=report_type)
#
#    def _get_report_details(self, data):
#        cr, uid = self.cr, self.uid
#        report_obj = self.pool.get('account.report')
#        datas =  []
#        balance = 0.0
#        name = data['form'].get('account_report_id') and data['form']['account_report_id'][1] or ''
#        report_id = data['form'].get('account_report_id') and data['form']['account_report_id'][0] or False
#        label = data['form']['label_filter'] or ''
#        datas.append({'id': report_id, 'label': label})
#        ctx = self.context.copy()
#        if report_id:
#            child_ids = report_obj.search(cr, uid, [('parent_id','=',report_id)])
#            child_ids.append(datas[0]['id'])
#            for child in report_obj.browse(cr, uid, child_ids, context=ctx):
#                balance = self.get_report_balance(child, child_ids, ctx)
#                if child.id == datas[0]['id']:
#                    datas[0].update({'name': child.name, 'balance': balance})
#                else:
#                    datas.append({'id': child.id, 'name': child.name, 'balance': balance, 'label': label})
#        return datas
#
#    def get_account_details(self, acc_id, data):
#        cr, uid = self.cr, self.uid
#        report_obj = self.pool.get('account.report')
#        accounts = []
#
#        ctx = self.context.copy()
#        ctx['fiscalyear'] = data['form'].get('fiscalyear_id', False)
#
#        if data['form']['filter'] == 'filter_period':
#            ctx['period_from'] = data['form'].get('period_from', False)
#            ctx['period_to'] =  data['form'].get('period_to', False)
#        elif data['form']['filter'] == 'filter_date':
#            ctx['date_from'] = data['form'].get('date_from', False)
#            ctx['date_to'] =  data['form'].get('date_to', False)
#
#        if acc_id and data['form'].get('account_details', False):
#            for rpt in report_obj.browse(cr, uid, [acc_id], context=ctx):
#                accounts = [acc for acc in rpt.account_ids if acc.level != 0]
#        return accounts

    def get_lines(self, data):
        lines = []
        ids2 = self.pool.get('account.low.level.report')._get_children_by_order(self.cr, self.uid, [data['form']['account_report_id'][0]], context=data['form']['used_context'])
        for report in self.pool.get('account.low.level.report').browse(self.cr, self.uid, ids2, context=data['form']['used_context']):
            vals = {
                'name': report.name,
                'balance': report.balance,
                'type': 'report',
            }
            if data['form']['enable_filter']:
                vals['balance_cmp'] = self.pool.get('account.low.level.report').browse(self.cr, self.uid, report.id, context=data['form']['comparison_context']).balance
            lines.append(vals)
            if report.type == 'accounts' and report.display_detail:
                for account in report.account_ids:
                    if account.level != 0:
                        vals = {
                            'name': account.code + ' ' + account.name,
                            'balance': account.balance,
                            'type': 'account',
                            'level': account.level,
                            'account_type': account.type,
                        }
                        if data['form']['enable_filter']:
                            vals['balance_cmp'] = self.pool.get('account.account').browse(self.cr, self.uid, account.id, context=data['form']['comparison_context']).balance
                        lines.append(vals)
        return lines

#    def get_report_balance(self, child, child_ids, context=None):
#        cr, uid = self.cr, self.uid
#        report_obj = self.pool.get('account.report')
#        balance = 0.0
#        # it's the sum of balance of the linked accounts
#        if child.type == 'accounts':
#            for a in child.account_ids:
#                balance += a.balance
#        # it's the balance of the linked account.report (so it means it's only a way to reuse figures coming from another report)
#        if child.type == 'account_report' and child.account_report_id:
#            for a in child.account_report_id.account_ids:
#                balance += a.balance
#        # it's the sum of balance of the children of this account.report (if there isn't, then it's 0.0)
#        if child.type == 'sum':
#            for child in report_obj.browse(cr, uid, child_ids, context=context):
#                for a in child.account_ids:
#                    balance += a.balance
#        return balance

report_sxw.report_sxw('report.account.low.level.report', 'account.low.level.report',
    'addons/account/report/account_low_level_report.rml', parser=report_account_common, header='internal')

