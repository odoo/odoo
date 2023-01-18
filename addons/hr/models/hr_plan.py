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
        activity_type_data = self.env['hr.plan.activity.type']._aggregate([('plan_id', 'in', self.ids)], ['*:count'], ['plan_id'])
        for plan in self:
            plan.steps_count = activity_type_data.get_agg(plan, '*:count', 0)
