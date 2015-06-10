# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _


class hr_department(models.Model):
    _inherit = 'hr.department'

    @api.multi
    def action_number_of_answers(self):
        self.ensure_one()
        action_hr_appraisal = self.env.ref('hr_appraisal.hr_appraisal_action_from_department').read()[0]
        action_hr_appraisal['display_name'] = _('Appraisal to Process')
        action_hr_appraisal['domain'] = str([('id', 'in', self.appraisal_process_ids.ids)])
        return action_hr_appraisal

    appraisal_process_ids = fields.One2many('hr.appraisal', 'department_id', domain=['&', ('state', '=', 'pending'), '|', ('date_close', '<=', fields.Datetime.now()), ('completed_user_input_ids.state', '=', 'done')], string='Appraisal to Process')
    appraisal_start_ids = fields.One2many('hr.appraisal', 'department_id', domain=[('state', '=', 'new')], string='Appraisal to Start')
