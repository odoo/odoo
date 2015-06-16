#-*- coding:utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from openerp.osv import osv
from openerp.report import report_sxw
from openerp.tools import amount_to_text_en

class payroll_advice_report(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(payroll_advice_report, self).__init__(cr, uid, name, context=context)

        self.localcontext.update({
            'time': time,
            'get_month': self.get_month,
            'convert': self.convert,
            'get_detail': self.get_detail,
            'get_bysal_total': self.get_bysal_total,
        })
        self.context = context
        
    def get_month(self, input_date):
        payslip_pool = self.pool.get('hr.payslip')
        res = {
               'from_name': '', 'to_name': ''
               }
        slip_ids = payslip_pool.search(self.cr, self.uid, [('date_from','<=',input_date), ('date_to','>=',input_date)], context=self.context)
        if slip_ids:
            slip = payslip_pool.browse(self.cr, self.uid, slip_ids, context=self.context)[0]
            from_date = datetime.strptime(slip.date_from, '%Y-%m-%d')
            to_date =  datetime.strptime(slip.date_to, '%Y-%m-%d')
            res['from_name']= from_date.strftime('%d')+'-'+from_date.strftime('%B')+'-'+from_date.strftime('%Y')
            res['to_name']= to_date.strftime('%d')+'-'+to_date.strftime('%B')+'-'+to_date.strftime('%Y')
        return res

    def convert(self, amount, cur):
        return amount_to_text_en.amount_to_text(amount, 'en', cur);

    def get_bysal_total(self):
        return self.total_bysal
        
    def get_detail(self, line_ids):
        result = []
        self.total_bysal = 0.00
        for l in line_ids:
            res = {}
            res.update({
                    'name': l.employee_id.name,
                    'acc_no': l.name,
                    'ifsc_code': l.ifsc_code,
                    'bysal': l.bysal,
                    'debit_credit': l.debit_credit,
                    })
            self.total_bysal += l.bysal
            result.append(res) 
        return result

class wrapped_report_payroll_advice(osv.AbstractModel):
    _name = 'report.l10n_in_hr_payroll.report_payrolladvice'
    _inherit = 'report.abstract_report'
    _template = 'l10n_in_hr_payroll.report_payrolladvice'
    _wrapped_report_class = payroll_advice_report
