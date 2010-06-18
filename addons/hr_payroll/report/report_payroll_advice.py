import time
import mx.DateTime
from report import report_sxw
from tools import amount_to_text_en

class payroll_advice_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(payroll_advice_report, self).__init__(cr, uid, name, context)
        
        self.total_amount = 0.00
        self.total_bysal = 0.00
        self.localcontext.update({
            'time': time,
            'get_month'   : self.get_month,
            'convert'     : self.convert,
            'get_detail'  : self.get_detail,
            'get_total'   : self.get_total,
            'get_bysal_total'   : self.get_bysal_total,
        })

    def get_month(self,input_date):
        res = {
               'mname':''
               }
        date = mx.DateTime.strptime(input_date, '%Y-%m-%d')
        res['mname']= date.strftime('%B')+'-'+date.strftime('%Y')
        return res
    
    def convert(self,amount, cur):
        amt_en = amount_to_text_en.amount_to_text(amount,'en',cur);
        return amt_en
    
    def get_bysal_total(self):
        return self.total_bysal

    def get_total(self):
        return self.total_amount
    
    def get_detail(self,line_ids):
        result =[]
        if line_ids:
            for l in line_ids:
                res = {}
                res['name'] = l.employee_id.name
                res['acc_no'] = l.name
                res['amount'] = l.amount
                res['bysal'] = l.bysal
                res['flag'] = l.flag
                self.total_amount += l.amount
                self.total_bysal += l.bysal
                result.append(res)
        return result
    
report_sxw.report_sxw('report.payroll.advice', 'hr.payroll.advice', 'hr_payroll/report/report_payroll_advice.rml', parser=payroll_advice_report)   