# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPlan(models.Model):
    _name = 'hr.plan'
    _description = 'plan'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    plan_activity_type_ids = fields.Many2many(
        'hr.plan.activity.type',
        string='Activities',
        domain="[('company_id', '=', company_id)]")
    active = fields.Boolean(default=True)
    steps_count = fields.Integer(compute='_compute_steps_count')

    @api.depends('plan_activity_type_ids')
    def _compute_steps_count(self):
        for plan in self:
            plan.steps_count = len(plan.plan_activity_type_ids)
