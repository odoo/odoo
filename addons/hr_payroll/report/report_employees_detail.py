#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import datetime
from report import report_sxw
import time
import pooler

class employees_salary_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(employees_salary_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_employee': self.get_employee,
            'get_employee_detail': self.get_employee_detail,
            'cal_monthly_amt': self.cal_monthly_amt,
            'get_periods': self.get_periods,
            'get_total': self.get_total,
            'get_allow': self.get_allow,
            'get_deduct': self.get_deduct,
            'get_other': self.get_other,
            'get_monthly_total': self.get_monthly_total,
        })

        self.mnths =[]
        self.allow_list =[]
        self.deduct_list = []
        self.other_list = []
        self.month_total_list =[]
        self.total=0.00

    def get_periods(self,form):
        self.mnths =[]
#       Get start year-month-date and end year-month-date
        fy = int(form['date_from'][0:4])
        ly = int(form['date_to'][0:4])

        fm = int(form['date_from'][5:7])
        lm = int(form['date_to'][5:7])
        no_months = (ly-fy)*12+lm-fm + 1
        cm = fm
        cy = fy

#       Get name of the months from integer
        mnth_name = []
        for count in range(0,no_months):
            m = datetime.date(cy, cm, 1).strftime('%b')
            mnth_name.append(m)
            self.mnths.append(str(cm)+'-'+str(cy))

            if cm == 12:
                cm = 0
                cy = ly
            cm = cm +1
        for c in range(0,(12-no_months)):
            mnth_name.append('None')
            self.mnths.append('None')
        return [mnth_name]

    def get_employee(self,form):
        result = []
        periods = []
        emp = pooler.get_pool(self.cr.dbname).get('hr.employee')
        emp_ids = form['employee_ids']
        result = emp.browse(self.cr,self.uid, emp_ids)
        return result

    def get_employee_detail(self,obj):
        self.month_total_list =['Net Total (Allowances with Basic - Deductions)',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00]
        self.allow_list =[]
        self.deduct_list = []
        self.other_list = []
        allowance_cat_ids =[]
        deduction_cat_ids = []
        other_cat_ids =[]
        self.total = 0.00
        payment_category = self.pool.get('hr.allounce.deduction.categoty')
        payslip = self.pool.get('hr.payslip')
        allowance_cat_ids = payment_category.search( self.cr, self.uid, [('type','=','allowance')])
        deduction_cat_ids = payment_category.search( self.cr, self.uid, [('type','=','deduction')])
        other_cat_ids = payment_category.search( self.cr, self.uid, [('type','in',('advance','loan','installment','otherpay','otherdeduct'))])
        #for Basic Salary
        res = []
        res = self.cal_monthly_amt(obj.id,False)
        self.total += res[len(res)-1]
        basic_flag = False
        for i in range(1,len(res)):
            if res[i] > 0.0:
                basic_flag = True
        if basic_flag:
            self.allow_list.append(res)
        #for allowance
        if allowance_cat_ids:
            for allow in allowance_cat_ids:
                 res = []
                 res = self.cal_monthly_amt(obj.id,allow)
                 all_flag = False
                 for i in range(1,len(res)):
                    if res[i] > 0.0:
                        all_flag = True
                 if all_flag:
                     self.allow_list.append(res)
                     self.total += res[len(res)-1]
        #for Deduction
        if deduction_cat_ids:
            for deduct in deduction_cat_ids:
                 res = []
                 res = self.cal_monthly_amt(obj.id,deduct)
                 ded_flag = False
                 for i in range(1,len(res)):
                    if res[i] > 0.0:
                        ded_flag = True
                 if ded_flag:
                     self.deduct_list.append(res)
                     self.total -= res[len(res)-1]
        #for Other
        if other_cat_ids:
            for other in other_cat_ids:
                 res = []
                 res = self.cal_monthly_amt(obj.id,other)
                 other_flag = False
                 for i in range(1,len(res)):
                    if res[i] > 0.0:
                        other_flag = True
                 if other_flag:
                     self.other_list.append(res)
        return None

    def cal_monthly_amt(self,emp_id,category):
        tot = 0.0
        cnt = 1
        result = []
        res ={}
        if not category:
            result.append('Basic Salary')
        else:
            category_name = self.pool.get('hr.allounce.deduction.categoty').read(self.cr, self.uid, [category],['name','type'])[0]
            result.append(category_name['name'])
        for mnth in self.mnths:
            if mnth <> 'None':
                if len(mnth) != 7:
                    mnth = '0' + str(mnth)
                query = "select id from hr_payslip where employee_id = "+str(emp_id)+" and to_char(date,'mm-yyyy') like '%"+mnth+"%' and state = 'done' "
                self.cr.execute(query)
                payslip_id = self.cr.dictfetchone()
            else:
                payslip_id = False
            if payslip_id:
                payslip_obj = self.pool.get('hr.payslip').browse(self.cr, self.uid, payslip_id['id'])
                if not category:
                    tot += payslip_obj.basic
                    res[mnth] = payslip_obj.basic
                    result.append(payslip_obj.basic)
                    self.month_total_list[cnt] = self.month_total_list[cnt] + payslip_obj.basic
                else:
                    append_index = 0
                    for line in payslip_obj.line_ids:
                        if line.category_id.id == category:
                            if category_name['type'] == 'allowance':
                                if res:
                                    self.month_total_list[cnt] = self.month_total_list[cnt] + line.total
                                    result[append_index] += line.total
                                    tot += line.total
                                    res[mnth] = result[append_index]
                                else:
                                    self.month_total_list[cnt] = self.month_total_list[cnt] + line.total
                                    tot += line.total
                                    res[mnth] = line.total
                                    append_index = len(result) - 1
                                    result.append(line.total)
                            if category_name['type'] == 'deduction':
                                if res:
                                    self.month_total_list[cnt] = self.month_total_list[cnt] - line.total
                                    result[append_index] += line.total
                                    tot += line.total
                                    res[mnth] = result[append_index]
                                else:
                                    self.month_total_list[cnt] = self.month_total_list[cnt] - line.total
                                    tot += line.total
                                    res[mnth] = line.total
                                    append_index = len(result) - 1
                                    result.append(line.total)
                            if category_name['type'] in ('advance','loan','installment','otherpay','otherdeduct'):
                                if res:
                                    result[append_index] += line.total
                                    tot += line.total
                                    res[mnth] = result[append_index]
                                else:
                                    res[mnth] = line.total
                                    result.append(res[mnth])
                                    append_index = len(result) - 1
                                    tot += line.total
            else:
                if mnth == 'None':
                    result.append('')
                    res[mnth] = ''
                    self.month_total_list[cnt] = ''
                else:
                    result.append(0.00)
                    res[mnth] = 0.00
            if not res:
                result.append(0.00)
            res = {}
            cnt = cnt + 1
        cnt = 1
        result.append(tot)
        tot = 0.0
        return result

    def get_allow(self):
        return self.allow_list

    def get_deduct(self):
        return self.deduct_list

    def get_other(self):
        return self.other_list

    def get_total(self):
        return self.total

    def get_monthly_total(self):
        return self.month_total_list

report_sxw.report_sxw('report.employees.salary', 'hr.payslip', 'hr_payroll/report/report_employees_detail.rml', parser=employees_salary_report,header='internal landscape')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
