# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    ongoing_appraisal_count = fields.Integer()
    last_appraisal_id = fields.Many2one(readonly=True)
    next_appraisal_date = fields.Date(compute='_compute_manager_only_fields', search='_search_next_appraisal_date')

    def _get_manager_only_fields(self):
        return super()._get_manager_only_fields() + ['next_appraisal_date']

    def _search_next_appraisal_date(self, operator, value):
        employees = self.env['hr.employee'].sudo().search([('id', 'child_of', self.env.user.employee_id.ids), ('next_appraisal_date', operator, value)])
        return [('id', 'in', employees.ids)]
