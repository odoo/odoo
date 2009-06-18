# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import pooler
import time
from report import report_sxw


class account_analytic_balance(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_analytic_balance, self).__init__(cr, uid, name, context)
        self.done_l = []
        self.localcontext.update( {
            'time': time,
            'lines_g': self._lines_g,
            'move_sum_debit': self._move_sum_debit,
            'move_sum_credit': self._move_sum_credit,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'sum_balance': self._sum_balance,
            'sum_quantity': self._sum_quantity,
            'move_sum_balance': self._move_sum_balance,
            'move_sum_quantity': self._move_sum_quantity,
        })

    def _lines_g(self, account_id, date1, date2):
        res = []
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids = account_analytic_obj.search(self.cr, self.uid,
                [('parent_id', 'child_of', [account_id])])
        temp_l = ids
        for id in ids:
            if id not in self.done_l:
                self.done_l.append(id)
            else:
                temp_l.remove(id)
        if temp_l:
            self.cr.execute("SELECT aa.name AS name, aa.code AS code, \
                        sum(aal.amount) AS balance, sum(aal.unit_amount) AS quantity \
                    FROM account_analytic_line AS aal, account_account AS aa \
                    WHERE (aal.general_account_id=aa.id) \
                        AND (aal.account_id in (" + ','.join(map(str, temp_l)) + "))\
                        AND (date>=%s) AND (date<=%s) AND aa.active \
                    GROUP BY aal.general_account_id, aa.name, aa.code, aal.code \
                    ORDER BY aal.code", (date1, date2))
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


    def _move_sum_debit(self, account_id, date1, date2):
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids = account_analytic_obj.search(self.cr, self.uid,
                [('parent_id', 'child_of', [account_id])])
        self.cr.execute("SELECT sum(amount) \
                FROM account_analytic_line \
                WHERE account_id in ("+ ','.join(map(str, ids)) +") \
                    AND date>=%s AND date<=%s AND amount>0",
                (date1, date2))
        return self.cr.fetchone()[0] or 0.0

    def _move_sum_credit(self, account_id, date1, date2):
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids = account_analytic_obj.search(self.cr, self.uid,
                [('parent_id', 'child_of', [account_id])])
        self.cr.execute("SELECT -sum(amount) \
                FROM account_analytic_line \
                WHERE account_id in ("+ ','.join(map(str, ids)) +") \
                    AND date>=%s AND date<=%s AND amount<0",
                (date1, date2))
        return self.cr.fetchone()[0] or 0.0

    def _move_sum_balance(self, account_id, date1, date2):
        debit = self._move_sum_debit(account_id, date1, date2)
        credit = self._move_sum_credit(account_id, date1, date2)
        return (debit-credit)

    def _move_sum_quantity(self, account_id, date1, date2):
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids = account_analytic_obj.search(self.cr, self.uid,
                [('parent_id', 'child_of', [account_id])])
        self.cr.execute("SELECT sum(unit_amount) \
                FROM account_analytic_line \
                WHERE account_id in ("+ ','.join(map(str, ids)) +") \
                    AND date>=%s AND date<=%s",
                (date1, date2))
        return self.cr.fetchone()[0] or 0.0


    def _sum_debit(self, accounts, date1, date2):
        ids = map(lambda x: x.id, accounts)
        if not len(ids):
            return 0.0
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids2 = account_analytic_obj.search(self.cr, self.uid,
                [('parent_id', 'child_of', ids)])
        self.cr.execute("SELECT sum(amount) \
                FROM account_analytic_line \
                WHERE account_id IN ("+','.join(map(str, ids2))+") \
                    AND date>=%s AND date<=%s AND amount>0",
                (date1, date2))
        return self.cr.fetchone()[0] or 0.0

    def _sum_credit(self, accounts, date1, date2):
        ids = map(lambda x: x.id, accounts)
        if not len(ids):
            return 0.0
        ids = map(lambda x: x.id, accounts)
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids2 = account_analytic_obj.search(self.cr, self.uid,
                [('parent_id', 'child_of', ids)])
        self.cr.execute("SELECT -sum(amount) \
                FROM account_analytic_line \
                WHERE account_id IN ("+','.join(map(str, ids2))+") \
                    AND date>=%s AND date<=%s AND amount<0",
                (date1, date2))
        return self.cr.fetchone()[0] or 0.0

    def _sum_balance(self, accounts, date1, date2):
        debit = self._sum_debit(accounts, date1, date2) or 0.0
        credit = self._sum_credit(accounts, date1, date2) or 0.0
        return (debit-credit)

    def _sum_quantity(self, accounts, date1, date2):
        ids = map(lambda x: x.id, accounts)
        if not len(ids):
            return 0.0
        account_analytic_obj = self.pool.get('account.analytic.account')
        ids2 = account_analytic_obj.search(self.cr, self.uid,
                [('parent_id', 'child_of', ids)])
        self.cr.execute("SELECT sum(unit_amount) \
                FROM account_analytic_line \
                WHERE account_id IN ("+','.join(map(str, ids2))+") \
                    AND date>=%s AND date<=%s",
                (date1, date2))
        return self.cr.fetchone()[0] or 0.0

report_sxw.report_sxw('report.account.analytic.account.balance',
        'account.analytic.account', 'addons/account/project/report/analytic_balance.rml',
        parser=account_analytic_balance, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

