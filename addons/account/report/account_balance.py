# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
from report import report_sxw

class account_balance(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_balance, self).__init__(cr, uid, name, context)
        self.sum_debit = 0.0
        self.sum_credit = 0.0
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'get_fiscalyear':self.get_fiscalyear,
            'get_periods':self.get_periods,
        })
        self.context = context
    
    def get_fiscalyear(self, form):
        fisc_id = form['fiscalyear']
        if fisc_id:
            self.cr.execute("select name from account_fiscalyear where id = %d" %(int(fisc_id)))
        else:
            self.cr.execute("select name from account_fiscalyear where state='draft'")
        res=self.cr.fetchall()
        result=''
        for r in res:
            result+=r[0]+","
        return str(result and result[:-1]) or ''


    def get_periods(self, form):
        periods=form['periods'][0][2]
        if periods:
            period_ids = ",".join([str(x) for x in form['periods'][0][2] if x])
            self.cr.execute("select name from account_period where id in (%s)" % (period_ids))
        else:
            if form['fiscalyear']:
                self.cr.execute("select name from account_period where fiscalyear_id = %d"%(int(form['fiscalyear'])))
            else:
                self.cr.execute("select name from account_period")
        res=self.cr.fetchall()
        result=''
        for r in res:
            result+=r[0]+","
        return str(result and result[:-1]) or ''

    def lines(self, form, ids={}, done=None, level=1):
        if not ids:
            ids = self.ids
        if not ids:
            return []
        if not done:
            done={}
        result = []
        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear']
        ctx['periods'] = form['periods'][0][2]
        ctx['target_move'] = form['target_move']
        accounts = self.pool.get('account.account').browse(self.cr, self.uid, ids, ctx)
        def cmp_code(x, y):
            return cmp(x.code, y.code)
        accounts.sort(cmp_code)
        for account in accounts:
            if account.id in done:
                continue
            done[account.id] = 1
            res = {
                'code': account.code,
                'name': account.name,
                'level': level,
                'debit': account.debit,
                'credit': account.credit,
                'balance': account.balance,
                'leef': not bool(account.child_id)
            }
            self.sum_debit += account.debit
            self.sum_credit += account.credit
            if not (res['credit'] or res['debit']) and not account.child_id:
                continue
            if account.child_id:
                def _check_rec(account):
                    if not account.child_id:
                        return bool(account.credit or account.debit)
                    for c in account.child_id:
                        if _check_rec(c):
                            return True
                    return False
                if not _check_rec(account):
                    continue

            result.append(res)
            if account.child_id:
                ids2 = [(x.code,x.id) for x in account.child_id]
                ids2.sort()
                result += self.lines(form, [x[1] for x in ids2], done, level+1)
        return result

    def _sum_credit(self):
        return self.sum_credit

    def _sum_debit(self):
        return self.sum_debit

report_sxw.report_sxw('report.account.account.balance', 'account.account', 'addons/account/report/account_balance.rml', parser=account_balance, header=2)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

