#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.report import report_sxw
from openerp.osv import osv
from openerp.addons.hr_payroll import report

class payslip_details_report_in(report.report_payslip_details.payslip_details_report):

    def __init__(self, cr, uid, name, context):
        super(payslip_details_report_in, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_details_by_rule_category': self.get_details_by_rule_category,
        })

class wrapped_report_payslipdetailsin(osv.AbstractModel):
    _name = 'report.l10n_in_hr_payroll.report_payslipdetails'
    _inherit = 'report.abstract_report'
    _template = 'l10n_in_hr_payroll.report_payslipdetails'
    _wrapped_report_class = payslip_details_report_in
