#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved
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
from datetime import datetime

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

report_sxw.report_sxw('report.payroll.advice', 'hr.payroll.advice', 'l10n_in_hr_payroll/report/report_payroll_advice.rml', parser=payroll_advice_report, header="external")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
