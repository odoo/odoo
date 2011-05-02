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

class report_payroll_register(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_payroll_register, self).__init__(cr, uid, name, context)

        self.total_amount = 0.00
        self.total_bysal = 0.00
        self.localcontext.update({
            'time': time,
            'get_month': self.get_month,
            'get_no': self.get_no,
            'get_basic':self.get_basic,
            'get_other':self.get_other,
            'get_allow':self.get_allow,
            'get_grows':self.get_grows,
            'get_deduct':self.get_deduct,
            'get_net':self.get_net,
            'add_line':self.add_line,
        })
        self.no = 0
        self.basic = 0.0
        self.other = 0.0
        self.allow = 0.0
        self.grows = 0.0
        self.deduct = 0.0
        self.net = 0.0

    def add_line(self, line):
        self.basic += line.basic
        self.other += line.other_pay
        self.allow += line.allounce
        self.grows += line.grows
        self.deduct += line.deduction
        self.net += line.net

    def get_basic(self,obj):
        for line in obj.line_ids:
            self.basic += line.basic
        return self.basic

    def get_other(self,obj):
        for line in obj.line_ids:
            self.other += line.other_pay
        return self.other

    def get_allow(self,obj):
        for line in obj.line_ids:
            self.allow += line.allounce
        return self.allow

    def get_grows(self,obj):
        for line in obj.line_ids:
            self.grows += line.grows
        return self.grows

    def get_deduct(self,obj):
        for line in obj.line_ids:
            self.deduct += line.deduction
        return self.deduct

    def get_net(self,obj):
        for line in obj.line_ids:
            self.net += line.net
        return self.net

    def get_month(self, indate):
        new_date = datetime.strptime(indate, '%Y-%m-%d')
        out_date = new_date.strftime('%B')+'-'+new_date.strftime('%Y')
        return out_date

    def get_no(self):
        self.no += 1
        return self.no

report_sxw.report_sxw(
    'report.hr.payroll.register.sheet',
    'hr.payroll.register',
    'hr_payroll/report/payroll_register.rml',
    parser=report_payroll_register
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
