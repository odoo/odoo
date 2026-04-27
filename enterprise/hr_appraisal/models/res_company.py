# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_default_appraisal_template(self):
        return self.env.ref('hr_appraisal.hr_appraisal_default_template', raise_if_not_found=False)

    def _get_default_appraisal_confirm_mail_template(self):
        return self.env.ref('hr_appraisal.mail_template_appraisal_confirm', raise_if_not_found=False)

    appraisal_plan = fields.Boolean(string='Automatically Generate Appraisals', default=True)
    assessment_note_ids = fields.One2many('hr.appraisal.note', 'company_id')
    appraisal_template_id = fields.Many2one(
        'hr.appraisal.template', default=_get_default_appraisal_template,
        string="Appraisal Template", check_company=True)
    appraisal_confirm_mail_template = fields.Many2one(
        'mail.template', domain="[('model', '=', 'hr.appraisal')]",
        default=_get_default_appraisal_confirm_mail_template)
    duration_after_recruitment = fields.Integer(string="Create an Appraisal after recruitment", default=6)
    duration_first_appraisal = fields.Integer(string="Create a first Appraisal after", default=6)
    duration_next_appraisal = fields.Integer(string="Create a second Appraisal after", default=12)

    _sql_constraints = [(
        'positif_number_months',
        'CHECK(duration_after_recruitment > 0 AND duration_first_appraisal > 0 AND duration_next_appraisal > 0)',
        "The duration time must be bigger or equal to 1 month."),
    ]

    @api.model
    def _get_default_assessment_note_ids(self):
        return [
            (0, 0, {'name': _('Needs improvement'), 'sequence': '1'}),
            (0, 0, {'name': _('Meets expectations'), 'sequence': '2'}),
            (0, 0, {'name': _('Exceeds expectations'), 'sequence': '3'}),
            (0, 0, {'name': _('Strongly Exceed Expectations'), 'sequence': '4'}),
        ]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        default_notes = self._get_default_assessment_note_ids()
        res.sudo().write({
            'assessment_note_ids': default_notes,
        })
        return res

    def _create_new_appraisal(self, employees):
        days = int(self.env['ir.config_parameter'].sudo().get_param('hr_appraisal.appraisal_create_in_advance_days', 8))
        appraisal_values = [{
            'company_id': employee.company_id.id,
            'employee_id': employee.id,
            'date_close': employee.next_appraisal_date + relativedelta(days=days),
            'manager_ids': employee.parent_id,
            'state': 'pending',
            'employee_feedback_published': False,
            'manager_feedback_published': False,
        } for employee in employees]
        return self.env['hr.appraisal'].create(appraisal_values)

    @api.model
    def _get_employee_start_date_field(self):
        self.ensure_one()
        return 'create_date'

    # CRON job
    def _run_employee_appraisal_plans(self):
        companies = self.env['res.company'].search([('appraisal_plan', '=', True)])
        current_date = datetime.date.today()
        all_employees = self.env['hr.employee'].search([('next_appraisal_date', '<=', current_date), ('company_id', 'in', companies.ids)])
        if all_employees:
            appraisals = self._create_new_appraisal(all_employees)
            # The cron creates appraisals in 'pending' state,
            # Thus we need to update last appraisal info on employee
            for appraisal in appraisals:
                appraisal.employee_id.sudo().write({
                    'last_appraisal_id': appraisal.id,
                    'last_appraisal_date': current_date,
                })
            appraisals._generate_activities()

