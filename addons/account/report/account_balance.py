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

import xml
import copy
from operator import itemgetter
import time
import datetime
from report import report_sxw

class account_balance(report_sxw.rml_parse):
        _name = 'report.account.account.balance'
        def __init__(self, cr, uid, name, context):
            super(account_balance, self).__init__(cr, uid, name, context)
            self.sum_debit = 0.00
            self.sum_credit = 0.00
            self.date_lst = []
            self.date_lst_string = ''
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
            res=[]
            if form.has_key('fiscalyear'):
                fisc_id = form['fiscalyear']
                if not (fisc_id):
                    return ''
                self.cr.execute("select name from account_fiscalyear where id = %s" , (int(fisc_id),))
                res=self.cr.fetchone()
            return res and res[0] or ''

        def get_periods(self, form):
            result=''
            if form.has_key('periods') and form['periods'][0][2]:
                period_ids = ",".join([str(x) for x in form['periods'][0][2] if x])
                self.cr.execute("select name from account_period where id in (%s)" % (period_ids))
                res=self.cr.fetchall()
                for r in res:
                    if (r == res[res.__len__()-1]):
                        result+=r[0]+". "
                    else:
                        result+=r[0]+", "
            return str(result and result[:-1]) or ''

        def transform_both_into_date_array(self,data):
            if not data['periods'][0][2] :
                periods_id =  self.pool.get('account.period').search(self.cr, self.uid, [('fiscalyear_id','=',data['form']['fiscalyear'])])
            else:
                periods_id = data['periods'][0][2]
            date_array = []
            for period_id in periods_id:
                period_obj = self.pool.get('account.period').browse(self.cr, self.uid, period_id)
                date_array = date_array + self.date_range(period_obj.date_start,period_obj.date_stop)

            period_start_date = date_array[0]
            date_start_date = data['date_from']
            period_stop_date = date_array[-1]
            date_stop_date = data['date_to']

            if period_start_date<date_start_date:
                start_date = period_start_date
            else :
                start_date = date_start_date

            if date_stop_date<period_stop_date:
                stop_date = period_stop_date
            else :
                stop_date = date_stop_date
            final_date_array = []
            final_date_array = final_date_array + self.date_range(start_date, stop_date)
            self.date_lst = final_date_array
            self.date_lst.sort()

        def transform_none_into_date_array(self,data):
            sql = "SELECT min(date) as start_date from account_move_line"
            self.cr.execute(sql)
            start_date = self.cr.fetchone()[0]
            sql = "SELECT max(date) as start_date from account_move_line"
            self.cr.execute(sql)
            stop_date = self.cr.fetchone()[0]
            array= []
            array = array + self.date_range(start_date, stop_date)
            self.date_lst = array
            self.date_lst.sort()

        def lines(self, form, ids={}, done=None, level=1):
            if not ids:
                ids = self.ids
            if not ids:
                return []
            if not done:
                done={}
            if form.has_key('Account_list') and form['Account_list']:
                ids = [form['Account_list']]
                del form['Account_list']
            res={}
            result_acc=[]
            ctx = self.context.copy()
            if form['state']=='byperiod' :
                self.transform_period_into_date_array(form)
                ctx['fiscalyear'] = form['fiscalyear']
                ctx['periods'] = form['periods'][0][2]
            elif form['state']== 'bydate':
                self.transform_date_into_date_array(form)
            elif form['state'] == 'all' :
                self.transform_both_into_date_array(form)
            elif form['state'] == 'none' :
                self.transform_none_into_date_array(form)

            accounts = self.pool.get('account.account').browse(self.cr, self.uid, ids, ctx)
            def cmp_code(x, y):
                return cmp(x.code, y.code)
            accounts.sort(cmp_code)
            for account in accounts:
                if account.id in done:
                    continue
                done[account.id] = 1
                res = {
                        'id' : account.id,
                        'type' : account.type,
                        'code': account.code,
                        'name': account.name,
                        'level': level,
                        'debit': account.debit,
                        'credit': account.credit,
                        'balance': account.balance,
                        'leef': not bool(account.child_id),
                        'bal_type':'',
                    }
                self.sum_debit += account.debit
                self.sum_credit += account.credit
                if account.child_id:
                    def _check_rec(account):
                        if not account.child_id:
                            return bool(account.credit or account.debit)
                        for c in account.child_id:
                            if not _check_rec(c) or _check_rec(c):
                                return True
                        return False
                    if not _check_rec(account) :
                        continue


                if form['display_account'] == 'bal_mouvement':
                    if res['credit'] > 0 or res['debit'] > 0 or res['balance'] > 0 :
                        result_acc.append(res)
                elif form['display_account'] == 'bal_solde':
                    if  res['balance'] > 0:
                        result_acc.append(res)
                else:
                    result_acc.append(res)
                if account.child_id:
                    acc_id = [acc.id for acc in account.child_id]
                    lst_string = ''
                    lst_string = '\'' + '\',\''.join(map(str,acc_id)) + '\''
                    self.cr.execute("select code,id from account_account where id IN (%s)"%(lst_string))
                    a_id = self.cr.fetchall()
                    a_id.sort()
                    ids2 = [x[1] for x in a_id]

                    result_acc += self.lines(form, ids2, done, level+1)

            return result_acc

        def date_range(self,start,end):
            start = datetime.date.fromtimestamp(time.mktime(time.strptime(start,"%Y-%m-%d")))
            end = datetime.date.fromtimestamp(time.mktime(time.strptime(end,"%Y-%m-%d")))
            full_str_date = []
        #
            r = (end+datetime.timedelta(days=1)-start).days
        #
            date_array = [start+datetime.timedelta(days=i) for i in range(r)]
            for date in date_array:
                full_str_date.append(str(date))
            return full_str_date

        #
        def transform_period_into_date_array(self,form):
            ## Get All Period Date
            if not form['periods'][0][2] :
                periods_id =  self.pool.get('account.period').search(self.cr, self.uid, [('fiscalyear_id','=',form['fiscalyear'])])
            else:
                periods_id = form['periods'][0][2]
            date_array = []
            for period_id in periods_id:
                period_obj = self.pool.get('account.period').browse(self.cr, self.uid, period_id)
                date_array = date_array + self.date_range(period_obj.date_start,period_obj.date_stop)

            self.date_lst = date_array
            self.date_lst.sort()

        def transform_date_into_date_array(self,form):
            return_array = self.date_range(form['date_from'],form['date_to'])
            self.date_lst = return_array
            self.date_lst.sort()

        def _sum_credit(self):
            return self.sum_credit

        def _sum_debit(self):
            return self.sum_debit

report_sxw.report_sxw('report.account.account.balance', 'account.account', 'addons/account/report/account_balance.rml', parser=account_balance, header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
