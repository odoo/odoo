# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    department_id = fields.Many2one('hr.department', compute='_compute_department_id')

    @api.depends('department_id')
    def _compute_plan_available_ids(self):
        todo = self.filtered(lambda s: s.res_model == 'hr.employee')
        for scheduler in todo:
            base_domain = self._get_plan_available_base_domain()
            if not scheduler.department_id:
                final_domain = expression.AND([base_domain, [('department_id', '=', False)]])
            else:
                final_domain = expression.AND([base_domain, ['|', ('department_id', '=', False), ('department_id', '=', self.department_id.id)]])
            scheduler.plan_available_ids = self.env['mail.activity.plan'].search(final_domain)
        super(MailActivitySchedule, self - todo)._compute_plan_available_ids()

    @api.depends('res_model_id', 'res_ids')
    def _compute_department_id(self):
        for wizard in self:
            if wizard.res_model == 'hr.employee':
                applied_on = wizard._get_applied_on_records()
                all_departments = applied_on.department_id
                wizard.department_id = False if len(all_departments) > 1 else all_departments
            else:
                wizard.department_id = False
