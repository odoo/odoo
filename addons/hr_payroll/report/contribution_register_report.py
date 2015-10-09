#-*- coding:utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ContributionRegisterReport(models.AbstractModel):
    _name = 'report.hr_payroll.report_contributionregister'

    def _get_payslip_lines(self, register):
        payslip_lines = []
        self.regi_total = 0.0
        self.env.cr.execute("SELECT pl.id from hr_payslip_line as pl "\
                        "LEFT JOIN hr_payslip AS hp on (pl.slip_id = hp.id) "\
                        "WHERE (hp.date_from >= %s) AND (hp.date_to <= %s) "\
                        "AND pl.register_id = %s "\
                        "AND hp.state = 'done' "\
                        "ORDER BY pl.slip_id, pl.sequence",
                        (self.date_from, self.date_to, register.id))
        payslip_lines = [x[0] for x in self.env.cr.fetchall()]
        lines = self.env['hr.payslip.line'].browse(payslip_lines)
        for line in lines:
            self.regi_total += line.total
        return lines

    @api.multi
    def render_html(self, data=None):
        self.model = self.env.context.get('active_model')
        contribution_regi = self.env[self.model].browse(self.env.context.get('active_ids'))
        self.date_from = data['form'].get('date_from', fields.Date.today())
        self.date_to = data['form'].get('date_to', fields.Date.from_string(fields.Datetime.now()) + relativedelta(months=+1, day=1, days=-1))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': contribution_regi,
            'data': data,
            'get_payslip_lines': self._get_payslip_lines(contribution_regi),
            'sum_total': self.regi_total
        }
        return self.env['report'].render('hr_payroll.report_contributionregister', docargs)
