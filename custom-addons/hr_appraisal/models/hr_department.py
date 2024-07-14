# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class hr_department(models.Model):
    _inherit = 'hr.department'

    appraisals_to_process_count = fields.Integer(compute='_compute_appraisals_to_process', string='Appraisals to Process')
    employee_feedback_template = fields.Html(
        compute='_compute_appraisal_feedbacks', store=True, readonly=False, translate=True)
    manager_feedback_template = fields.Html(
        compute='_compute_appraisal_feedbacks', store=True, readonly=False, translate=True)
    custom_appraisal_templates = fields.Boolean(string="Custom Appraisal Templates", default=False)
    appraisal_properties_definition = fields.PropertiesDefinition('Appraisal Properties')

    def _compute_appraisals_to_process(self):
        appraisals = self.env['hr.appraisal']._read_group(
            [('department_id', 'in', self.ids), ('state', 'in', ['new', 'pending'])], ['department_id'], ['__count'])
        result = {department.id: count for department, count in appraisals}
        for department in self:
            department.appraisals_to_process_count = result.get(department.id, 0)

    @api.depends('company_id')
    def _compute_appraisal_feedbacks(self):
        for department in self:
            department.employee_feedback_template = department.company_id.appraisal_employee_feedback_template or self.env.company.appraisal_employee_feedback_template
            department.manager_feedback_template = department.company_id.appraisal_manager_feedback_template or self.env.company.appraisal_manager_feedback_template
