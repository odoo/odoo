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

from datetime import datetime
from report import report_sxw
from tools import amount_to_text_en

class payslip_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(payslip_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
                'convert': self.convert,
                'get_month': self.get_month,
                'get_earnings': self.get_earnings,
                'get_deductions':self.get_deductions,
                'get_leave':self.get_leave,
                'get_others':self.get_others,
                })

    def convert(self, amount, cur):
        amt_en = amount_to_text_en.amount_to_text(amount, 'en', cur)
        return amt_en

    def get_others(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].category_id.type in ('advance', 'loan', 'otherpay', 'otherdeduct', 'installment'):
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_leave(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].type == 'leaves':
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_earnings(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].category_id.type == 'allowance' and obj[id].type != 'leaves':
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_deductions(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].category_id.type == 'deduction' and obj[id].type != 'leaves':
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_month(self, obj):
        res = {
                'mname':''
        }
        date = datetime.strptime(obj.date, '%Y-%m-%d')
        res['mname']= date.strftime('%B')+"-"+date.strftime('%Y')
        return res['mname']

report_sxw.report_sxw('report.payslip.pdf', 'hr.payslip', 'hr_payroll/report/payslip.rml', parser=payslip_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: