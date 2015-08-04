# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _


class hr_department(models.Model):
    _inherit = 'hr.department'

    @api.multi
    def _compute_appraisals_to_process(self):
        appraisals = self.env['hr.appraisal'].read_group(
            [('department_id', 'in', self.ids), ('state', 'in', ['new', 'pending'])], ['department_id'], ['department_id'])
        result = dict((data['department_id'][0], data['department_id_count']) for data in appraisals)
        for department in self:
            department.appraisals_to_process_count = result.get(department.id, 0)

    appraisals_to_process_count = fields.Integer(compute='_compute_appraisals_to_process', string='Appraisals to Process')
