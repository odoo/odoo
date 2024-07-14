# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

class HrSalaryAttachmentReport(models.Model):
    _name = 'hr.salary.attachment.report'
    _description = 'Salary Attachment / Report'
    _auto = False

    # TODO: this is the old reporting, we can have more accurate data from the new salary_attachment
    # TODO: redo this

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Name", readonly=True)
    payslip_start_date = fields.Date(readonly=True)
    payslip_end_date = fields.Date(readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    attachment_amount = fields.Float(string="Attachment of Salary", readonly=True)
    assignment_amount = fields.Float(string="Assignment of Salary", readonly=True)
    child_support_amount = fields.Float(string="Child Support", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE or REPLACE view %s as (
                SELECT
                    row_number() OVER() AS id,
                    p.id AS payslip_id,
                    p.employee_id,
                    p.company_id,
                    p.date_from as payslip_start_date,
                    p.date_to as payslip_end_date,
                    CASE WHEN pl.code = 'ATTACH_SALARY' THEN pl.amount END AS attachment_amount,
                    CASE WHEN pl.code = 'ASSIG_SALARY' THEN pl.amount END AS assignment_amount,
                    CASE WHEN pl.code = 'CHILD_SUPPORT' THEN pl.amount END AS child_support_amount
                FROM hr_payslip p
                LEFT JOIN hr_payslip_line pl on (pl.slip_id = p.id)
                WHERE pl.code IN ('ATTACH_SALARY', 'ASSIG_SALARY', 'CHILD_SUPPORT') and p.state = 'paid'
            );
        """ % self._table)
