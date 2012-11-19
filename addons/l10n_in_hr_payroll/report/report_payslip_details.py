#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved
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

from report import report_sxw
from hr_payroll import report

class payslip_details_report_in(report.report_payslip_details.payslip_details_report):

    def __init__(self, cr, uid, name, context):
        super(payslip_details_report_in, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_details_by_rule_category': self.get_details_by_rule_category,
        })

report_sxw.report_sxw('report.paylip.details.in', 'hr.payslip', 'l10n_in_hr_payroll/report/report_payslip_details.rml', parser=payslip_details_report_in)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: