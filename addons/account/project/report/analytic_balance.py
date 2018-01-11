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

import time
from openerp.osv import osv
from openerp.report import report_sxw


class account_analytic_balance(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_analytic_balance, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'time': time,
            'get_objects': self._get_objects,
            'lines_g': self._lines_g,
            'move_sum': self._move_sum,
            'sum_all': self._sum_all,
            'sum_balance': self._sum_balance,
            'move_sum_balance': self._move_sum_balance,
        })
        self.acc_ids = []
        self.read_data = []
        self.empty_acc = False
        self.acc_data_dict = {}# maintains a relation with an account with its successors.
        self.acc_sum_list = []# maintains a list of all ids

    def get_children(self, ids):
        read_data = self.pool.get('account.analytic.account').read(self.cr, self.uid, ids,['child_ids','code','complete_name','balance'])
        for data in read_data:
            if (data['id'] not in self.acc_ids):
                inculde_empty =  True
                if (not self.empty_acc) and data['balance'] == 0.00:
                    inculde_empty = False
                if inculde_empty:
                    self.acc_ids.append(data['id'])
                    self.read_data.append(data)
                    if data['child_ids']:
                        self.get_children(data['child_ids'])
        return True

    def _get_objects(self, empty_acc):
        if self.read_data:
            return self.read_data
        self.empty_acc = empty_acc
        self.read_data = []
        self.get_children(self.ids)
        return self.read_data

    def _lines_g(self, account_id, date1, date2):
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids = account_analytic_obj.search(self.cr, self.uid,
                [('parent_id', 'child_of', [account_id])])
        self.cr.execute("SELECT aa.name AS name, aa.code AS code, \
                    sum(aal.amount) AS balance, sum(aal.unit_amount) AS quantity \
                FROM account_analytic_line AS aal, account_account AS aa \
                WHERE (aal.general_account_id=aa.id) \
                    AND (aal.account_id IN %s)\
                    AND (date>=%s) AND (date<=%s) AND aa.active \
                GROUP BY aal.general_account_id, aa.name, aa.code, aal.code \
                ORDER BY aal.code", (tuple(ids), date1, date2))
        res = self.cr.dictfetchall()

        for r in res:
            if r['balance'] > 0:
                r['debit'] = r['balance']
                r['credit'] = 0.0
            elif r['balance'] < 0:
                r['debit'] = 0.0
                r['credit'] = -r['balance']
            else:
                r['balance'] == 0
                r['debit'] = 0.0
                r['credit'] = 0.0
        return res

    def _move_sum(self, account_id, date1, date2, option):
        if account_id not in self.acc_data_dict:
            account_analytic_obj = self.pool.get('account.analytic.account')
            ids = account_analytic_obj.search(self.cr, self.uid,[('parent_id', 'child_of', [account_id])])
            self.acc_data_dict[account_id] = ids
        else:
            ids = self.acc_data_dict[account_id]

        query_params = (tuple(ids), date1, date2)
        if option == "credit":
            self.cr.execute("SELECT COALESCE(-sum(amount),0.0) FROM account_analytic_line \
                    WHERE account_id IN %s AND date>=%s AND date<=%s AND amount<0",query_params)
        elif option == "debit":
            self.cr.execute("SELECT COALESCE(sum(amount),0.0) FROM account_analytic_line \
                    WHERE account_id IN %s\
                        AND date>=%s AND date<=%s AND amount>0",query_params)
        elif option == "quantity":
            self.cr.execute("SELECT COALESCE(sum(unit_amount),0.0) FROM account_analytic_line \
                WHERE account_id IN %s\
                    AND date>=%s AND date<=%s",query_params)
        return self.cr.fetchone()[0] or 0.0

    def _move_sum_balance(self, account_id, date1, date2):
        debit = self._move_sum(account_id, date1, date2, 'debit')
        credit = self._move_sum(account_id, date1, date2, 'credit')
        return (debit-credit)

    def _sum_all(self, accounts, date1, date2, option):
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids = map(lambda x: x['id'], accounts)
        if not ids:
            return 0.0

        if not self.acc_sum_list:
            ids2 = account_analytic_obj.search(self.cr, self.uid,[('parent_id', 'child_of', ids)])
            self.acc_sum_list = ids2
        else:
            ids2 = self.acc_sum_list

        query_params = (tuple(ids2), date1, date2)
        if option == "debit":
            self.cr.execute("SELECT COALESCE(sum(amount),0.0) FROM account_analytic_line \
                    WHERE account_id IN %s AND date>=%s AND date<=%s AND amount>0",query_params)
        elif option == "credit":
            self.cr.execute("SELECT COALESCE(-sum(amount),0.0) FROM account_analytic_line \
                    WHERE account_id IN %s AND date>=%s AND date<=%s AND amount<0",query_params)
        elif option == "quantity":
            self.cr.execute("SELECT COALESCE(sum(unit_amount),0.0) FROM account_analytic_line \
                    WHERE account_id IN %s AND date>=%s AND date<=%s",query_params)
        return self.cr.fetchone()[0] or 0.0

    def _sum_balance(self, accounts, date1, date2):
        debit = self._sum_all(accounts, date1, date2, 'debit') or 0.0
        credit = self._sum_all(accounts, date1, date2, 'credit') or 0.0
        return (debit-credit)


class report_analyticbalance(osv.AbstractModel):
    _name = 'report.account.report_analyticbalance'
    _inherit = 'report.abstract_report'
    _template = 'account.report_analyticbalance'
    _wrapped_report_class = account_analytic_balance

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
