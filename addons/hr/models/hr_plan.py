# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPlan(models.Model):
    _name = 'hr.plan'
    _description = 'plan'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', check_company=True)
    plan_activity_type_ids = fields.One2many(
        'hr.plan.activity.type', 'plan_id',
        string='Activities',
        domain="[('company_id', '=', company_id)]")
    active = fields.Boolean(default=True)
    steps_count = fields.Integer(compute='_compute_steps_count')

    @api.depends('plan_activity_type_ids')
    def _compute_steps_count(self):
        activity_type_data = self.env['hr.plan.activity.type']._read_group([('plan_id', 'in', self.ids)], ['plan_id'], ['plan_id'])
        steps_count = {x['plan_id'][0]: x['plan_id_count'] for x in activity_type_data}
        for plan in self:
            plan.steps_count = steps_count.get(plan.id, 0)
