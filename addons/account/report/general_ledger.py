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
import pooler

class general_ledger(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(general_ledger, self).__init__(cr, uid, name, context)
        self.localcontext.update( {
            'time': time,
            'lines': self.lines,
            'sum_debit_account': self._sum_debit_account,
            'sum_credit_account': self._sum_credit_account,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'check_lines': self.check_lines,

        })
        self.context = context
        self.tmp_list2=[]
        self.final_list=[]


    def recur(self,list1):
        tmp_list3 =list1
        self.tmp_list2 =list1
#       print "self list",self.tmp_list2
        for i in range(0,len(list1)):
            if list1[i] in self.final_list:
                continue
            self.final_list.append(list1[i])
#           print "finallly",self.final_list
            if list1[i].child_id:

                tmp_list4=(hasattr(list1[i],'child_id') and list(list1[i].child_id) or [])

                self.tmp_list2 +=tmp_list4

                self.tmp_list2+=self.recur(tmp_list4)

        return self.final_list

    def repeatIn(self, lst, name,nodes_parent=False):

        if name=='o':
            list_final=[]
            if not lst:
                return  super(general_ledger,self).repeatIn(lst, name,nodes_parent)
            try:
                tmp_list = list(lst)
                if tmp_list:
                    tmp_list = self.recur(tmp_list)
                else:
                    return  super(general_ledger,self).repeatIn(lst, name,nodes_parent)

                lst = list(set([x for x in tmp_list]))

                final={}
#               for x in lst:
#                   final[x]=x.id
#               final1=sorted(final.items(), lambda x, y: cmp(x[1], y[1]))
#
#               for a in final1:
#                   list_final.append(a[0])
                list_final=tmp_list

            except:
                pass
        else:

            list_final=lst
        ret_data = super(general_ledger,self).repeatIn(list_final, name,nodes_parent)

        return ret_data

    def check_lines(self, account, form):
        result = self.lines(account, form, history=True)
        res = [{'code':account.code,'name':account.name}]
        if not result:
            res = []
        return res

    def lines(self, account, form, history=False):
        self.ids +=[account.id]
        if not account.check_history and not history:
            return []

        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear']
        ctx['periods'] = form['periods'][0][2]
        ctx['state']=form['state']
        query = self.pool.get('account.move.line')._query_get(self.cr, self.uid, context=ctx)
        self.cr.execute("SELECT l.date, j.code, l.ref, l.name, l.debit, l.credit "\
            "FROM account_move_line l, account_journal j "\
            "WHERE l.journal_id = j.id "\
                "AND account_id = %d AND "+query+" "\
            "ORDER by l.id", (account.id,))
        res = self.cr.dictfetchall()
        sum = 0.0

        for l in res:
            sum += l['debit'] - l ['credit']
            l['progress'] = sum
        return res

    def _sum_debit_account(self, account, form):
        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear']
        ctx['periods'] = form['periods'][0][2]
        ctx['state']=form['state']
        query = self.pool.get('account.move.line')._query_get(self.cr, self.uid, context=ctx)
        self.cr.execute("SELECT sum(debit) "\
                "FROM account_move_line l "\
                "WHERE l.account_id = %d AND "+query, (account.id,))
        return self.cr.fetchone()[0] or 0.0

    def _sum_credit_account(self, account, form):
        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear']
        ctx['periods'] = form['periods'][0][2]
        ctx['state']=form['state']
        query = self.pool.get('account.move.line')._query_get(self.cr, self.uid, context=ctx)
        self.cr.execute("SELECT sum(credit) "\
                "FROM account_move_line l "\
                "WHERE l.account_id = %d AND "+query, (account.id,))
        return self.cr.fetchone()[0] or 0.0

    def _sum_debit(self, form):
        if not self.ids:
            return 0.0
        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear']
        ctx['periods'] = form['periods'][0][2]
        ctx['state']=form['state']
        query = self.pool.get('account.move.line')._query_get(self.cr, self.uid, context=ctx)
        self.cr.execute("SELECT sum(debit) "\
                "FROM account_move_line l "\
                "WHERE l.account_id in ("+','.join(map(str, self.ids))+") AND "+query)

        return self.cr.fetchone()[0] or 0.0

    def _sum_credit(self, form):
        if not self.ids:
            return 0.0
        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear']
        ctx['periods'] = form['periods'][0][2]
        ctx['state']=form['state']
        query = self.pool.get('account.move.line')._query_get(self.cr, self.uid, context=ctx)
        self.cr.execute("SELECT sum(credit) "\
                "FROM account_move_line l "\
                "WHERE l.account_id in ("+','.join(map(str, self.ids))+") AND "+query)
        return self.cr.fetchone()[0] or 0.0

report_sxw.report_sxw('report.account.general.ledger', 'account.account', 'addons/account/report/general_ledger.rml', parser=general_ledger, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

