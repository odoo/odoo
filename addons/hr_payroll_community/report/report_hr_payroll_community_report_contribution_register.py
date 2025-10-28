# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReportHrPayrollCommunityReportContributionRegister(models.AbstractModel):
    """Create new model for getting Contribution Register Report"""
    _name = 'report.hr_payroll_community.report_contributionregister'
    _description = 'Payroll Contribution Register Report'

    def _get_payslip_lines(self, register_ids, date_from, date_to):
        """Function for getting Payslip Lines to Contribution Register Report"""
        result = {}
        self.env.cr.execute("""
            SELECT pl.id from hr_payslip_line as pl
            LEFT JOIN hr_payslip AS hp on (pl.slip_id = hp.id)
            WHERE (hp.date_from >= %s) AND (hp.date_to <= %s)
            AND pl.register_id in %s
            AND hp.state = 'done'
            ORDER BY pl.slip_id, pl.sequence""",
                            (date_from, date_to, tuple(register_ids)))
        line_ids = [x[0] for x in self.env.cr.fetchall()]
        for line in self.env['hr.payslip.line'].browse(line_ids):
            result.setdefault(line.register_id.id, self.env['hr.payslip.line'])
            result[line.register_id.id] += line
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        """Function for getting Contribution Register Values"""
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        register_ids = self.env.context.get('active_ids', [])
        contrib_registers = self.env['hr.contribution.register'].browse(
            register_ids)
        date_from = data['form'].get('date_from', fields.Date.today())
        date_to = data['form'].get('date_to',
                                   str(datetime.now() + relativedelta(months=+1,
                                                                      day=1,
                                                                      days=-1))[
                                   :10])
        lines_data = self._get_payslip_lines(register_ids, date_from, date_to)
        lines_total = {}
        for register in contrib_registers:
            lines = lines_data.get(register.id)
            lines_total[register.id] = lines and sum(
                lines.mapped('total')) or 0.0
        return {
            'doc_ids': docids,
            'doc_model': 'hr.contribution.register',
            'docs': contrib_registers,
            'data': data,
            'lines_data': lines_data,
            'lines_total': lines_total
        }
