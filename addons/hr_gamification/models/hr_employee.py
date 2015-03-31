# -*- coding: utf-8 -*-

from openerp import api, fields, models


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    goal_ids = fields.One2many('gamification.goal', string='Employee HR Goals', compute='_compute_employee_goals')
    badge_ids = fields.One2many('gamification.badge.user', string='Employee Badges', compute='_compute_employee_badges')
    has_badges = fields.Boolean(compute='_compute_has_badges')

    @api.one
    def _compute_employee_goals(self):
        self.goal_ids = self.env['gamification.goal'].search([
            ('user_id', '=', self.user_id.id),
            ('challenge_id.category', '=', 'hr')
        ])

    @api.one
    def _compute_employee_badges(self):
        self.badge_ids = self.env['gamification.badge.user'].search([
            '|',
                ('employee_id', '=', self.id),
                '&',
                    ('employee_id', '=', False),
                    ('user_id', '=', self.user_id.id)
            ])

    @api.one
    def _compute_has_badges(self):
        employee_badges_count = self.env['gamification.badge.user'].search_count([
                '|',
                    ('employee_id', '=', self.id),
                    '&',
                        ('employee_id', '=', False),
                        ('user_id', '=', self.user_id.id)
                ])
        self.has_badges = employee_badges_count > 0
