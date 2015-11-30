#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api
from odoo.addons.hr_payroll import report

#while converting hr_payroll module into new api following error was occurring
#   File "/home/odoo/runbot/extra/runbot/static/build/115894-9122-87dc2e/openerp/models.py", line 643, in _build_model
#    model.__init__(pool, cr)
#    TypeError: __init__() takes exactly 5 arguments (3 given)
#to resolve this, converting the code into new api.


class payslip_details_report_in(report.payslip_details_report.PayslipDetailsReport):
    _name = 'report.l10n_in_hr_payroll.report_payslipdetails'

    @api.multi
    def render_html(self, data=None):
        records = self.env['hr.payslip'].browse(self.env.context.get('active_ids'))
        docargs = {
            'doc_ids': self.env.context.get('active_ids'),
            'doc_model': report.model,
            'docs': records,
            'data': data,
            'get_details_by_rule_category': self.get_details_by_rule_category,
        }
        return self.env['report'].render('l10n_in_hr_payroll.report_payslipdetails', docargs)
