# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
from openerp.report import report_sxw
from openerp.tools import amount_to_text_en

class report_print_check(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_print_check, self).__init__(cr, uid, name, context)
        self.number_lines = 0
        self.number_add = 0
        self.localcontext.update({
            'time': time,
            'get_lines': self.get_lines,
            'fill_stars' : self.fill_stars,
        })
    def fill_stars(self, amount):
        amount = amount.replace('Dollars','')
        if len(amount) < 100:
            stars = 100 - len(amount)
            return ' '.join([amount,'*'*stars])

        else: return amount
    
    def get_lines(self, voucher_lines):
        result = []
        self.number_lines = len(voucher_lines)
        for i in range(0, min(10,self.number_lines)):
            if i < self.number_lines:
                res = {
                    'date_due' : voucher_lines[i].date_due,
                    'name' : voucher_lines[i].name,
                    'amount_original' : voucher_lines[i].amount_original and voucher_lines[i].amount_original or False,
                    'amount_unreconciled' : voucher_lines[i].amount_unreconciled and voucher_lines[i].amount_unreconciled or False,
                    'amount' : voucher_lines[i].amount and voucher_lines[i].amount or False,
                }
            else :
                res = {
                    'date_due' : False,
                    'name' : False,
                    'amount_original' : False,
                    'amount_due' : False,
                    'amount' : False,
                }
            result.append(res)
        return result

report_sxw.report_sxw(
    'report.account.print.check.top',
    'account.voucher',
    'addons/account_check_writing/report/check_print_top.rml',
    parser=report_print_check,header=False
)

report_sxw.report_sxw(
    'report.account.print.check.middle',
    'account.voucher',
    'addons/account_check_writing/report/check_print_middle.rml',
    parser=report_print_check,header=False
)

report_sxw.report_sxw(
    'report.account.print.check.bottom',
    'account.voucher',
    'addons/account_check_writing/report/check_print_bottom.rml',
    parser=report_print_check,header=False
)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
