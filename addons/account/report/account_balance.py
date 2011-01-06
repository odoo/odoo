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
            super(account_balance, self).__init__(cr, uid, name, context=context)
            self.result_acc = []
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
                res = self.cr.fetchall()
                len_res = len(res) 
                for r in res:
                    if (r == res[len_res-1]):
                        result+=r[0]+". "
                    else:
                        result+=r[0]+", "
            else:
                fy_obj = self.pool.get('account.fiscalyear').browse(self.cr,self.uid,form['fiscalyear'])
                res = fy_obj.period_ids
                len_res = len(res)
                for r in res:
                    if r == res[len_res-1]:
                        result+=r.name+". "
                    else:
                        result+=r.name+", "
                
            return str(result and result[:-1]) or ''

        
        def lines(self, form, ids={}, done=None, level=1):
            def _process_child(accounts,disp_acc,parent,level):
                account_rec = [acct for acct in accounts if acct['id']==parent][0]
                res = {
                        'id' : account_rec['id'],
                        'type' : account_rec['type'],
                        'code': account_rec['code'],
                        'name': account_rec['name'],
                        'level': level,
                        'debit': account_rec['debit'],
                        'credit': account_rec['credit'],
                        'balance': account_rec['balance'],
                       # 'leef': not bool(account['child_id']),
                        'parent_id':account_rec['parent_id'],
                        'bal_type':'',
                    }
                self.sum_debit += account_rec['debit']
                self.sum_credit += account_rec['credit']
                if disp_acc == 'bal_mouvement':
                    if res['credit'] > 0 or res['debit'] > 0 or res['balance'] > 0 :
                        self.result_acc.append(res)
                elif disp_acc == 'bal_solde':
                    if  res['balance'] != 0:
                        self.result_acc.append(res)
                else:
                    self.result_acc.append(res)
                if account_rec['child_id']:
                    for child in account_rec['child_id']:
                        level += 1
                        _process_child(accounts,disp_acc,child,level)
            if not ids:
                ids = self.ids
            if not ids:
                return []
            if not done:
                done={}
            if form.has_key('Account_list') and form['Account_list']:
                ids = [form['Account_list']]
                del form['Account_list']
            ctx = self.context.copy()
            ctx['state'] = form['context'].get('state','all')
            ctx['fiscalyear'] = form['fiscalyear']
            if form['state']=='byperiod' :
                ctx['periods'] = form['periods'][0][2]
            elif form['state']== 'bydate':
                ctx['date_from'] = form['date_from']
                ctx['date_to'] =  form['date_to'] 
            elif form['state'] == 'all' :
                ctx['periods'] = form['periods'][0][2]
                ctx['date_from'] = form['date_from']
                ctx['date_to'] =  form['date_to']
            parents = ids
            child_ids = self.pool.get('account.account')._get_children_and_consol(self.cr, self.uid, ids, ctx)
            if child_ids:
                ids = child_ids
            accounts = self.pool.get('account.account').read(self.cr, self.uid, ids,['type','code','name','debit','credit','balance','parent_id','child_id'], ctx)
            for parent in parents:
                level = 1
                if parent in done:
                    continue
                done[parent] = 1
                _process_child(accounts,form['display_account'],parent,level)
            return self.result_acc
        
        def _sum_credit(self):
            return self.sum_credit

        def _sum_debit(self):
            return self.sum_debit

report_sxw.report_sxw('report.account.account.balance', 'account.account', 'addons/account/report/account_balance.rml', parser=account_balance, header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
