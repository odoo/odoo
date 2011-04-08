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
from datetime import datetime
from report import report_sxw
from tools import amount_to_text_en

class payroll_advice_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(payroll_advice_report, self).__init__(cr, uid, name, context)

        self.total_amount = 0.00
        self.total_bysal = 0.00
        self.localcontext.update({
            'time': time,
            'get_month': self.get_month,
            'convert': self.convert,
            'get_detail': self.get_detail,
            'get_total': self.get_total,
            'get_bysal_total': self.get_bysal_total,
        })

    def get_month(self,input_date):
        res = {
               'mname': ''
               }
        date = datetime.strptime(input_date, '%Y-%m-%d')
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
