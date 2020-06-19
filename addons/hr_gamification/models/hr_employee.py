# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    goal_ids = fields.One2many('gamification.goal', string='Employee HR Goals', compute='_compute_employee_goals')
    badge_ids = fields.One2many(
        'gamification.badge.user', string='Employee Badges', compute='_compute_employee_badges',
        help="All employee badges, linked to the employee either directly or through the user"
    )
    has_badges = fields.Boolean(compute='_compute_employee_badges')
    # necessary for correct dependencies of badge_ids and has_badges
    direct_badge_ids = fields.One2many(
        'gamification.badge.user', 'employee_id',
        help="Badges directly linked to the employee")

    @api.depends('user_id.goal_ids.challenge_id.challenge_category')
    def _compute_employee_goals(self):
        for employee in self:
            employee.goal_ids = self.env['gamification.goal'].search([
                ('user_id', '=', employee.user_id.id),
                ('challenge_id.challenge_category', '=', 'hr'),
            ])

    @api.depends('direct_badge_ids', 'user_id.badge_ids.employee_id')
    def _compute_employee_badges(self):
        for employee in self:
            badge_ids = self.env['gamification.badge.user'].search([
                '|', ('employee_id', '=', employee.id),
                     '&', ('employee_id', '=', False),
                          ('user_id', '=', employee.user_id.id)
            ])
            employee.has_badges = bool(badge_ids)
            employee.badge_ids = badge_ids
