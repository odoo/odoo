# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models, _


class hr_department(models.Model):
    _inherit = 'hr.department'

    appraisals_to_process_count = fields.Integer(compute='_compute_appraisals_to_process', string='Appraisals to Process')
    custom_appraisal_template_id = fields.Many2one('hr.appraisal.template', string="Appraisal Templates", compute='_compute_appraisal_feedbacks', store=True, readonly=False, check_company=True)
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
            department.custom_appraisal_template_id = department.company_id.appraisal_template_id

    def action_open_appraisals(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_appraisal.action_appraisal_report_all")
        action['context'] = {
            **ast.literal_eval(action['context']),
            'search_default_department_id': self.id,
        }
        return action
