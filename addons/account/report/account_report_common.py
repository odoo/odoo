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
            'time': time,
            'get_report_details': self._get_report_details,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_sortby': self._get_sortby,
            'get_filter': self._get_filter,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_company':self._get_company,
            'get_account_details': self.get_account_details,
        })
        self.context = context

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
        return super(report_account_common, self).set_context(objects, data, new_ids, report_type=report_type)

    def _get_report_details(self, data):
        cr, uid = self.cr, self.uid
        report_obj = self.pool.get('account.report')
        datas =  []
        balance = 0.0
        name = data['form'].get('account_report_id') and data['form']['account_report_id'][1] or ''
        report_id = data['form'].get('account_report_id') and data['form']['account_report_id'][0] or False
        datas.append({'id': report_id})
        if report_id:
            child_ids = report_obj.search(cr, uid, [('parent_id','=',report_id)])
            child_ids.append(datas[0]['id'])
            for child in report_obj.browse(cr, uid, child_ids):
                if child.type == 'accounts':
                    for a in child.account_ids:
                        balance += a.balance
                # it's the balance of the linked account.report (so it means it's only a way to reuse figures coming from another report)
                if child.type == 'account_report' and child.account_report_id:
                    for a in child.account_report_id.account_ids:
                        balance +=a.balance
                #it's the sum of balance of the children of this account.report (if there isn't, then it's 0.0)
                if child.type == 'sum':
                    for child in report_obj.browse(cr, uid, child_ids):
                        for a in child.account_ids:
                            balance += a.balance
                if child.id == datas[0]['id']:
                    datas[0].update({'name': child.name, 'balance': balance})
                else:
                    datas.append({'id': child.id, 'name': child.name, 'balance': balance})
        return datas

    def get_account_details(self, acc_id, data):
        cr, uid = self.cr, self.uid
        report_obj = self.pool.get('account.report')
        accounts = []
        if acc_id and data['form'].get('display_details_per_account', False):
            for rpt in report_obj.browse(cr, uid, [acc_id]):
                for acc in rpt.account_ids:
                    accounts.append({'code': acc.code, 'name': acc.name, 'bal': acc.balance})
        return accounts

    def get_report_balance(self):
        balance = 0.0
        return balance

report_sxw.report_sxw('report.account.common', 'account.account',
    'addons/account/report/account_report_common.rml', parser=report_account_common, header='internal')

