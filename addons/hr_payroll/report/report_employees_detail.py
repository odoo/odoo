import time
import locale
import datetime
from report import report_sxw
import time
import pooler
import rml_parse
import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime

class employees_salary_report(rml_parse.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(employees_salary_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_employee' : self.get_employee,
            'get_employee_detail' : self.get_employee_detail,
            'cal_monthly_amt':self.cal_monthly_amt,
            'get_periods'  : self.get_periods,
            'get_fiscalyear' : self.get_fiscalyear,
            'get_total' : self.get_total,
            'get_allow':self.get_allow,
            'get_deduct':self.get_deduct,
            'get_other':self.get_other,
            'get_monthly_total':self.get_monthly_total,
        })
        
        self.mnths =[]
        self.allow_list =[]
        self.deduct_list = []
        self.other_list = []
        self.month_total_list =[]
        self.curr_fiscal_year_name=''
        self.period_ids = []
        self.total=0.00
    
    def get_periods(self,form):
        self.mnths =[]
        fiscalyear = pooler.get_pool(self.cr.dbname).get('account.fiscalyear')
        curr_fiscalyear_id = form['fiscalyear_id']
        curr_fiscalyear = fiscalyear.read(self.cr,self.uid,[form['fiscalyear_id']],['date_start','date_stop'])[0]
        
#       Get start year-month-date and end year-month-date
        fy = int(curr_fiscalyear['date_start'][0:4])    
        ly = int(curr_fiscalyear['date_stop'][0:4])
        
        fm = int(curr_fiscalyear['date_start'][5:7])
        lm = int(curr_fiscalyear['date_stop'][5:7])
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
        return [mnth_name]

    def get_fiscalyear(self,fiscalyear_id):
        fiscalyear_obj = pooler.get_pool(self.cr.dbname).get('account.fiscalyear')
        return fiscalyear_obj.read(self.cr,self.uid,[fiscalyear_id],['name'])[0]['name']

    def get_employee(self,form):
        result = []   
        periods = []    
        emp = pooler.get_pool(self.cr.dbname).get('hr.employee')     
        emp_ids = form['employee_ids'][0][2]
        result = emp.browse(self.cr,self.uid, emp_ids)
        fiscalyear_obj = pooler.get_pool(self.cr.dbname).get('account.fiscalyear').browse(self.cr, self.uid, form['fiscalyear_id'])
        period_ids_l = fiscalyear_obj.period_ids
        for period in period_ids_l:
            periods.append(period.id)
        self.period_ids = ','.join(map(str, periods))
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
        allowance_cat_ids = payment_category.search( self.cr, self.uid, [('type','=','allow')])
        deduction_cat_ids = payment_category.search( self.cr, self.uid, [('type','=','deduct')])
        other_cat_ids = payment_category.search( self.cr, self.uid, [('type','=','other')])
        #for Basic Salary
        res = []
        res = self.cal_monthly_amt(obj.id,None)
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
            if len(mnth) != 7:
                mnth = '0' + str(mnth)
            query = "select id from hr_payslip where employee_id = "+str(emp_id)+" and to_char(date,'mm-yyyy') like '%"+mnth+"%' and state = 'done' and period_id in "+"("+ self.period_ids +")" +""
            self.cr.execute(query)
            payslip_id = self.cr.dictfetchone()
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
                            if category_name['type'] == 'allow':
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
                            if category_name['type'] == 'deduct':
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
                            if category_name['type'] == 'other':
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
    
report_sxw.report_sxw('report.employees.salary', 'hr.payslip', 'hr_payroll/report/report_employees_detail.rml', parser=employees_salary_report)
       
       
               
