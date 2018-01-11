#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
from dateutil import relativedelta
from openerp.osv import osv
from openerp.report import report_sxw


class contribution_register_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(contribution_register_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_payslip_lines': self._get_payslip_lines,
            'sum_total': self.sum_total,
        })

    def set_context(self, objects, data, ids, report_type=None):
        self.date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))
        self.date_to = data['form'].get('date_to', str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
        return super(contribution_register_report, self).set_context(objects, data, ids, report_type=report_type)

    def sum_total(self):
        return self.regi_total

    def _get_payslip_lines(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        payslip_lines = []
        res = []
        self.regi_total = 0.0
        self.cr.execute("SELECT pl.id from hr_payslip_line as pl "\
                        "LEFT JOIN hr_payslip AS hp on (pl.slip_id = hp.id) "\
                        "WHERE (hp.date_from >= %s) AND (hp.date_to <= %s) "\
                        "AND pl.register_id = %s "\
                        "AND hp.state = 'done' "\
                        "ORDER BY pl.slip_id, pl.sequence",
                        (self.date_from, self.date_to, obj.id))
        payslip_lines = [x[0] for x in self.cr.fetchall()]
        for line in payslip_line.browse(self.cr, self.uid, payslip_lines):
            res.append({
                'payslip_name': line.slip_id.name,
                'name': line.name,
                'code': line.code,
                'quantity': line.quantity,
                'amount': line.amount,
                'total': line.total,
            })
            self.regi_total += line.total
        return res


class wrapped_report_contribution_register(osv.AbstractModel):
    _name = 'report.hr_payroll.report_contributionregister'
    _inherit = 'report.abstract_report'
    _template = 'hr_payroll.report_contributionregister'
    _wrapped_report_class = contribution_register_report

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
