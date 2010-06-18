import time
import locale
import datetime
from report import report_sxw
import time
import pooler
import rml_parse
import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime

class year_salary_report(rml_parse.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(year_salary_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_employee' : self.get_employee,
            'get_periods'  : self.get_periods,
            'get_months_tol' : self.get_months_tol,
            'get_fiscalyear' : self.get_fiscalyear,
            'get_total' : self.get_total,
        })
        
        self.mnths =[]
        self.mnths_tol = []
        self.curr_fiscal_year_name=''
        self.total=0.0
        
    def get_periods(self,form):
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
        ls1=[]        
        ls = []
        periods = []
        tol_mnths=['Total',0,0,0,0,0,0,0,0,0,0,0,0]     
        emp = pooler.get_pool(self.cr.dbname).get('hr.employee')     
        emp_ids = form['employee_ids'][0][2]
        empll  = emp.browse(self.cr,self.uid, emp_ids)
        fiscalyear_obj = pooler.get_pool(self.cr.dbname).get('account.fiscalyear').browse(self.cr, self.uid, form['fiscalyear_id'])
        period_ids_l = fiscalyear_obj.period_ids
        for period in period_ids_l:
            periods.append(period.id)
        periods_ids = ','.join(map(str, periods))
        cnt = 1
        for emp_id in empll:        
            ls1.append(emp_id.name)
            tol = 0.0
            for mnth in self.mnths:
                if len(mnth) != 7:
                    mnth = '0' + str(mnth)
                query = "select net from hr_payslip where employee_id = "+str(emp_id.id)+" and to_char(date,'mm-yyyy') like '%"+mnth+"%' and state = 'done' and period_id in "+"("+ periods_ids +")" +""
                self.cr.execute(query)
                sal = self.cr.fetchall()
                try:
                    ls1.append(sal[0][0])
                except:
                    ls1.append(0) 
                try:                    
                    tol += sal[0][0]
                    tol_mnths[cnt] = tol_mnths[cnt] + sal[0][0]
                except:
                    tol += 0 
                cnt = cnt + 1  
            cnt = 1          
            ls1.append(tol)
            ls.append(ls1)
            ls1 = []
        self.mnths_tol.append(tol_mnths)
        return ls
    
    def get_months_tol(self):
        return self.mnths_tol
        
    def get_total(self):
        for item in self.mnths_tol:
            for count in range(1,len(item)):
              self.total += item[count]
        return self.total
    
report_sxw.report_sxw('report.year.salary', 'hr.payslip', 'hr_payroll/report/report_year_report.rml', parser=year_salary_report)
       
       
               
