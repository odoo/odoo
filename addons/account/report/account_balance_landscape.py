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
import locale
from report import report_sxw

parents = {
    'tr':1,
    'li':1,
    'story': 0,
    'section': 0
}

class account_balance_landscape(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_balance_landscape, self).__init__(cr, uid, name, context=context)
        self.flag=1
        self.dr_total= 0.00
        self.cr_total= 0.00
        self.parent_bal=0
        self.status=0
        self.done_total=0
        self.baldiv={}
        self.empty_parent=0
        self.result_total = {}
        self.total_for_perc=[]
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'get_lines':self.get_lines,
            'linesForTotal': self.linesForTotal,
            'linesForYear': self.linesForYear,
            'get_years':self.get_years,
            'cal_total':self.cal_total,
            'total_dr':self.total_dr,
            'total_cr':self.total_cr
            })
        self.context = context

    def linesForYear(self,form):
        temp=0
        years={}

        global pattern
        global show
        global perc
        global bal_zero
        global ref_bal

        pattern=form['compare_pattern']

        if form['show_columns']!=1:
            show=0
        else:
            show=form['show_columns']

        if form['format_perc']!=1:
            perc=0
        else:
            perc=form['format_perc']

        if form['account_choice']=='bal_zero':
            bal_zero=0
        else:
            bal_zero=1

        ctx = self.context.copy()

        if perc==1:
            if form['select_account']!=False:
                ref_ac=self.pool.get('account.account').browse(self.cr, self.uid, form['select_account'], ctx.copy())
                if ref_ac.balance<>0.00:
                    ref_bal=ref_ac.balance
                else:
                    ref_bal=1.00
            else:
                ref_bal='nothing'
        else:
            ref_bal='nothing'


        self.done_total=1
        self.total_for_perc=self.linesForTotal(form, ids={}, doneAccount={}, level=1)
        self.done_total=0

        for t1 in range(0,len(form['fiscalyear'])):
            locale.setlocale(locale.LC_ALL, '')
            self.result_total["sum_credit" + str(t1)]=locale.format("%.2f", self.result_total["sum_credit" + str(t1)], grouping=True)
            self.result_total["sum_debit" + str(t1)]=locale.format("%.2f", self.result_total["sum_debit" + str(t1)], grouping=True)

        for temp in range(0,len(form['fiscalyear'])):
            fy=self.pool.get('account.fiscalyear').name_get(self.cr, self.uid, form['fiscalyear'][temp])
            years["year"+str(temp)]=fy[0][1][12:16]

        return [years]


    def linesForTotal(self, form, ids={}, doneAccount={}, level=1):
        if not self.done_total==1:
            return [self.result_total]
        accounts=[]
        if not ids:
            ids = self.ids
        if not ids:
            return []

        ctx = self.context.copy()

        for id in form['fiscalyear']:
            tmp=[]

            ctx['fiscalyear'] = id
            ctx['periods'] = form['periods']
            ctx['period_manner'] = form['period_manner']
            ctx['state'] = form['context'].get('state','all')
            tmp = self.pool.get('account.account').browse(self.cr, self.uid, ids, ctx.copy())

            if tmp:
                accounts.append(tmp)

        merged_accounts=zip(*accounts)
        # used to check for the frst record so all sum_credit and sum_debit r set to 0.00
        if level==1:
            doneAccount={}
        for entry in merged_accounts:

            if entry[0].id in doneAccount:
                continue
            doneAccount[entry[0].id] = 1

            for k in range(0,len(entry)):
                temp_credit=0.00
                temp_debit=0.00
                if entry[0].type <> 'view':
                    temp_credit+=entry[k].credit
                    temp_debit+=entry[k].debit

                if self.flag==1:
                    self.result_total["sum_credit" + str(k)]=0.00
                    self.result_total["sum_debit" + str(k)]=0.00

                if form['account_choice']=='bal_zero':
                    if temp_credit<>temp_debit:
                        self.result_total["sum_credit" + str(k)]+=temp_credit
                        self.result_total["sum_debit" + str(k)]+=temp_debit
                else:
                    self.result_total["sum_credit" + str(k)]+=temp_credit
                    self.result_total["sum_debit" + str(k)]+=temp_debit

            self.flag=2

            if entry[0].child_id:
                ids2 = [(x.code,x.id) for x in entry[0].child_id]
                ids2.sort()

                result_total_parent = self.linesForTotal(form, [x[1] for x in ids2], doneAccount, level+1)

        return [self.result_total]

    def lines(self, form, ids={}, done={}, level=1):
        accounts=[]
        if not ids:
            ids = self.ids
        if not ids:
            return []
        result = []
        ctx = self.context.copy()
        tmp1=[]
        for id in form['fiscalyear']:

            ctx['fiscalyear'] = id
            ctx['periods'] = form['periods']
            ctx['period_manner']=form['period_manner']
            ctx['state'] = form['context'].get('state','all')
            tmp1 = self.pool.get('account.account').browse(self.cr, self.uid, ids, ctx.copy())

            if tmp1:
                accounts.append(tmp1)

        if level==1:   #if parent is called,done is not empty when called again.
            done={}

        def cmp_code(x, y):
            return cmp(x.code, y.code)
        for n in range(0,len(accounts)):
            accounts[n].sort(cmp_code)
        merged_accounts=zip(*accounts)

        for entry in merged_accounts:
            j=0
            checked=1

            if form['account_choice']!='all':    #  if checked,include empty a/c;not otherwise
                checked=0

            if entry[0].id in done:
                continue
            done[entry[0].id] = 1

            if entry[0].child_id:  # this is for parent account,dont check 0 for it
                checked=4
                self.status=1 # for displaying it Bold
            else:
                self.status=0
            if checked==0:
                i=0
                for i in range(0,len(entry)):
                    if bal_zero==0:
                        if entry[i].balance<>0.0:
                            checked=4
                            break
                        else:
                            checked=3
                            i=i+1
                    else:
                        if entry[i].credit <> 0.0 or entry[i].debit <> 0.0:
                            checked=4
                            break
                        else:
                            checked=3
                            i=i+1

            if checked==3:
                # this is the point where we skip those accounts which are encountered as empty ones
                continue
                self.empty_parent=0
            else:
                self.empty_parent=1
                res = {
                    'code': entry[0].code,
                    'name': entry[0].name,
                    'level': level,
                    'status': self.status,
                    }

                for j in range(0,len(entry)):

                    locale.setlocale(locale.LC_ALL, '')
                    res["debit"+str(j)]=locale.format("%.2f", entry[j].debit, grouping=True)
                    res["credit"+str(j)]=locale.format("%.2f", entry[j].credit, grouping=True)
                    res["balance"+str(j)]=locale.format("%.2f", entry[j].balance, grouping=True)


                    if j==0:
                        res["bal_cash"+str(j)]="0.00"
                        res["bal_perc"+str(j)]="0.00%"
                    else:
                        temp_cash=entry[j].balance - entry[j-1].balance
                        res["bal_cash"+str(j)]=locale.format("%.2f", temp_cash, grouping=True)
                        if entry[j-1].balance<>0.00:
                            temp_perc=(entry[j].balance - entry[j-1].balance )*100/entry[j-1].balance
                        else:
                            temp_perc=(entry[j].balance) *100

                        res["bal_perc"+str(j)]=locale.format("%.2f", temp_perc) + "%"


                    if ref_bal=='nothing':
                        if level==1:
                            self.parent_bal=1
                        else:
                            self.parent_bal=0

                        if self.parent_bal==1:
                            res["balance_perc"+str(j)]="/"
                        else:
                            if entry[j].balance==0.00:
                                if self.baldiv["baldiv"+str(level-1)+str(j)]<>0.00:
                                    res["balance_perc"+str(j)]="0.00%"
                                else:
                                    res["balance_perc"+str(j)]="/"
                            else:
                                if self.baldiv["baldiv"+str(level-1)+str(j)]<>0.00:
                                    temp=self.baldiv["baldiv"+str(level-1)+str(j)]
                                    temp1=(entry[j].balance * 100 )/ float(temp)
                                    temp1=round(temp1,2)
                                    res["balance_perc" + str(j)]=str(temp1)+"%"
                                else:
                                    res["balance_perc"+str(j)]="/"
                    else:
                        res["balance_perc"+str(j)]=str( (entry[j].balance * 100 )/ float(ref_bal)) + "%"

            result.append(res)

            if entry[0].child_id:

                for q in range(0,len(form['fiscalyear'])):
                    self.baldiv["baldiv"+str(level)+str(q)]=entry[q].balance

                ids2 = [(x.code,x.id) for x in entry[0].child_id]
                ids2.sort()
                dir=[]
                dir += self.lines(form, [x[1] for x in ids2], done, level+1)
                if dir==[]:
                    for w in range(0,len(form['fiscalyear'])):
                        if entry[w].credit <> 0.0 or entry[w].debit <> 0.0 or entry[w].balance<>0.00:
                            dont_pop=1
                            break
                        else:
                            dont_pop=0
                    if dont_pop==1:
                        result +=dir
                    else:
                        result.pop(-1)   # here we pop up the parent having its children as emprty accounts
                else:
                    result +=dir

        return result

    def get_years(self, form):
        result =[]
        res={}
        for temp in range(0, len(form['fiscalyear'])):
            res={}
            fy=self.pool.get('account.fiscalyear').name_get(self.cr, self.uid, form['fiscalyear'][temp])
            res['year']=fy[0][1]
            res['last_str']=temp

            result.append(res)
        self.linesForYear(form)
        return result

    def get_lines(self, year_dict, form):
        final_result = []
        res = {}
        line_l = self.lines(form)
        self.cal_total(year_dict)
        if line_l:
            for l in line_l:
                res = {}
                res['code'] = l['code']
                res['name'] = l['name']
                res['level'] = l['level']
                for k,v in l.items():
                    if k.startswith('debit'+str(year_dict['last_str'])):
                        res['debit'] = v
                    if k.startswith('credit'+str(year_dict['last_str'])):
                        res['credit'] = v
                    if k.startswith('balance'+str(year_dict['last_str'])) and not k.startswith('balance_perc'+str(year_dict['last_str'])):
                        res['balance'] =v
                    if k.startswith('balance_perc'+str(year_dict['last_str'])) and not k.startswith('balance'+str(year_dict['last_str'])):
                        res['balance_perc'] = v
                    if form['compare_pattern'] == 'bal_perc':
                        if k.startswith('bal_perc'+str(year_dict['last_str'])):
                            res['pattern'] = v
                    elif form['compare_pattern'] == 'bal_cash':
                        if k.startswith('bal_cash'+str(year_dict['last_str'])):
                            res['pattern'] = v
                    else:
                        res['pattern'] = ''
                final_result.append(res)
        return final_result

    def cal_total(self, year_dict):
        total_l = self.result_total
        if total_l:
            for k,v in total_l.items():
                if k.startswith('sum_debit'+str(year_dict['last_str'])):
                    self.dr_total = v
                elif k.startswith('sum_credit'+str(year_dict['last_str'])):
                    self.cr_total = v
                else:
                    continue
        return True

    def total_dr(self):
        return self.dr_total

    def total_cr(self):
        return self.cr_total

report_sxw.report_sxw('report.account.account.balance.landscape', 'account.account', 'addons/account/report/account_balance_landscape.rml', parser=account_balance_landscape, header="internal landscape")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

