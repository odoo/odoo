#-*- coding:utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
from openerp.report import report_sxw


class payslip_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(payslip_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_payslip_lines': self.get_payslip_lines,
        })

    def get_payslip_lines(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].appears_on_payslip is True:
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res


class wrapped_report_payslip(osv.AbstractModel):
    _name = 'report.hr_payroll.report_payslip'
    _inherit = 'report.abstract_report'
    _template = 'hr_payroll.report_payslip'
    _wrapped_report_class = payslip_report
