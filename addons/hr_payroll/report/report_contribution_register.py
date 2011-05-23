#!/usr/bin/env python
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
from dateutil import relativedelta

from report import report_sxw

class contribution_register_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(contribution_register_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_payslip_lines': self._get_payslip_lines,
        })

    def set_context(self, objects, data, ids, report_type=None):
        self.date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))
        self.date_to = data['form'].get('date_to', str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
        return super(contribution_register_report, self).set_context(objects, data, ids, report_type=report_type)

    def _get_payslip_lines(self, obj):
        payslip_obj = self.pool.get('hr.payslip')
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        result = {}

        self.cr.execute("SELECT pl.id, pl.slip_id from hr_payslip_line as pl "\
                        "LEFT JOIN hr_payslip AS hp on (pl.slip_id = hp.id) "\
                        "WHERE (hp.date_from >= %s) AND (hp.date_to <= %s) "\
                        "AND pl.register_id = %s "\
                        "GROUP BY pl.slip_id, pl.sequence, pl.id, pl.category_id "\
                        "ORDER BY pl.sequence",
                        (self.date_from, self.date_to, obj.id))
        for x in self.cr.fetchall():
            result.setdefault(x[1], [])
            result[x[1]].append(x[0])
        for key, value in result.iteritems():
            res.append({
                'payslip_name': payslip_obj.browse(self.cr, self.uid, [key])[0].name,
            })
            for line in payslip_line.browse(self.cr, self.uid, value):
                res.append({
                            'name': line.name,
                            'code': line.code,
                            'total': line.total,
                })
        return res

report_sxw.report_sxw('report.contribution.register.lines', 'hr.contribution.register', 'hr_payroll/report/report_contribution_register.rml', parser=contribution_register_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: