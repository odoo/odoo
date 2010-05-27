# -*- encoding: utf-8 -*-
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

import pooler
import time
import mx.DateTime
import rml_parse
from report import report_sxw
from account_report_india.report import report_pl

class report_balancesheet_horizontal(rml_parse.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_balancesheet_horizontal, self).__init__(cr, uid, name, context)
        self.obj_pl=report_pl.report_pl_account_horizontal(cr, uid, name, context)
        self.result_sum_dr=0.0
        self.result_sum_cr=0.0
        self.result = {}
        self.res_pl={}
        self.result_temp=[]
        self.localcontext.update({
            'time': time,
            'get_lines' : self.get_lines,
            'get_lines_another' : self.get_lines_another,
            'get_company': self.get_company,
            'get_currency': self._get_currency,
            'sum_dr' : self.sum_dr,
            'sum_cr' : self.sum_cr,
            'get_data':self.get_data,
            'get_pl_balance':self.get_pl_balance,
            
        })
        self.context = context
        
    def sum_dr(self):
        if self.res_pl['type'] == 'Net Profit':
            self.result_sum_dr += self.res_pl['balance']
        return self.result_sum_dr or 0.0
     
    def sum_cr(self):
        if self.res_pl['type'] == 'Net Loss':
            self.result_sum_cr += self.res_pl['balance']
        return self.result_sum_cr or 0.0

    def get_pl_balance(self):
        return self.res_pl or 0.0
    
    def get_data(self,form):
        cr, uid = self.cr, self.uid
        db_pool = pooler.get_pool(self.cr.dbname)
        
        #Getting Profit or Loss Balance from profit and Loss report
        result_pl=self.obj_pl.get_data(form)
        self.res_pl=self.obj_pl.final_result()
        
        type_pool = db_pool.get('account.account.type')
        account_pool = db_pool.get('account.account')
        year_pool = db_pool.get('account.fiscalyear')

        types = [
            'liability',
            'asset'
        ]

        ctx = self.context.copy()
        ctx['state'] = form['context'].get('state','all')
        ctx['fiscalyear'] = form['fiscalyear']
        if form['state']=='byperiod' :
            ctx['periods'] = form['periods']
        elif form['state']== 'bydate':
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']
        elif form['state'] == 'all' :
            ctx['periods'] = form['periods']
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']

        cal_list={}
        pl_dict = {}
        account_dict = {}
        account_id = [form['Account_list']]
        account_ids = account_pool._get_children_and_consol(cr, uid, account_id, context=ctx)
        accounts = account_pool.browse(cr, uid, account_ids, context=ctx)

        if self.res_pl['type'] == 'Net Profit C.F.B.L.':
            self.res_pl['type'] = 'Net Profit'
        else:
            self.res_pl['type'] = 'Net Loss'
        pl_dict  = {
            'code' : False,
            'name' : self.res_pl['type'],
            'level': False,
            'balance':self.res_pl['balance'],
        }
        for typ in types:
            accounts_temp = []
            for account in accounts:
                if (account.user_type.report_type) and (account.user_type.report_type == typ):
                    account_dict = {
                        'id'   : account.id,
                        'code' : account.code,
                        'name' : account.name,
                        'level': account.level,
                        'balance':account.balance,
                    }
                    if typ == 'liability' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_dr += abs(account.debit - account.credit)
                    if typ == 'asset' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_cr += abs(account.debit - account.credit)
                    if form['display_account'] == 'bal_mouvement':
                        if account.credit > 0 or account.debit > 0 or account.balance > 0 :
                            accounts_temp.append(account_dict)
                    elif form['display_account'] == 'bal_solde':
                        if  account.balance != 0:
                            accounts_temp.append(account_dict)
                    else:
                        accounts_temp.append(account_dict)
                    if account.id == form['reserve_account_id']:
                        pl_dict['level'] = account['level'] + 1
                        accounts_temp.append(pl_dict)
                        
            self.result[typ] = accounts_temp
            cal_list[typ]=self.result[typ]

        if cal_list:
            temp={}
            for i in range(0,max(len(cal_list['liability']),len(cal_list['asset']))):
                if i < len(cal_list['liability']) and i < len(cal_list['asset']):
                    temp={
                          'code' : cal_list['liability'][i]['code'],
                          'name' : cal_list['liability'][i]['name'],
                          'level': cal_list['liability'][i]['level'],
                          'balance':cal_list['liability'][i]['balance'],
                          'code1' : cal_list['asset'][i]['code'],
                          'name1' : cal_list['asset'][i]['name'],
                          'level1': cal_list['asset'][i]['level'],
                          'balance1':cal_list['asset'][i]['balance'],
                          }
                    self.result_temp.append(temp)
                else:
                    if i < len(cal_list['asset']):
                        temp={
                              'code' : '',
                              'name' : '',
                              'level': False,
                              'balance':False,
                              'code1' : cal_list['asset'][i]['code'],
                              'name1' : cal_list['asset'][i]['name'],
                              'level1': cal_list['asset'][i]['level'],
                              'balance1':cal_list['asset'][i]['balance'],
                          }
                        self.result_temp.append(temp)
                    if  i < len(cal_list['liability']): 
                        temp={
                              'code' : cal_list['liability'][i]['code'],
                              'name' : cal_list['liability'][i]['name'],
                              'level': cal_list['liability'][i]['level'],
                              'balance':cal_list['liability'][i]['balance'],
                              'code1' : '',
                              'name1' : '',
                              'level1': False,
                              'balance1':False,
                          }
                        self.result_temp.append(temp)
        return None
    
    def get_lines(self):
        return self.result_temp

    def get_lines_another(self, group):
        return self.result.get(group, [])
    
    def _get_currency(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.code

    def get_company(self,form):
        comp_obj=pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr,self.uid,form['company_id'])
        return comp_obj.name 

report_sxw.report_sxw('report.account.balancesheet.horizontal', 'account.account',
    'addons/account_report_india/report/report_balance_sheet_horizontal.rml',parser=report_balancesheet_horizontal,
    header=False)

report_sxw.report_sxw('report.account.balancesheet', 'account.account',
    'addons/account_report_india/report/report_balance_sheet.rml',parser=report_balancesheet_horizontal,
    header=False)
