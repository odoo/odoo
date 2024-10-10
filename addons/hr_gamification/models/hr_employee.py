# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    goal_ids = fields.One2many('gamification.goal', string='Employee HR Goals', compute='_compute_employee_goals')
    has_badges = fields.Boolean(compute='_compute_employee_badges')
    badge_ids = fields.One2many(
        'gamification.badge.user', string='Employee Badges', compute='_compute_employee_badges',
        help="All employee badges, linked to the employee either directly or through the user"
    )

    @api.depends('user_id.goal_ids.challenge_id.challenge_category')
    def _compute_employee_goals(self):
        for employee in self:
            employee.goal_ids = self.env['gamification.goal'].search([
                ('user_id', '=', employee.user_id.id),
                ('challenge_id.challenge_category', '=', 'hr'),
            ])

    @api.depends('user_id.badge_ids')
    def _compute_employee_badges(self):
        badge_read_group = self.env['gamification.badge.user']._read_group(
            domain=[('user_id', 'in', self.user_id.ids)],
            groupby=['user_id'],
            aggregates=['id:recordset'])
        badges_per_user = dict(badge_read_group)
        for employee in self:
            employee_badges = badges_per_user.get(employee.user_id, self.env['gamification.badge.user'])
            employee.has_badges = bool(employee_badges)
            employee.badge_ids = employee_badges
