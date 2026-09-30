from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    badge_ids = fields.One2many('gamification.badge.user', readonly=True, compute='_compute_badge_ids')
    has_badges = fields.Boolean(compute='_compute_has_badges')

    def _compute_has_badges(self):
        self._compute_from_employee('has_badges')

    def _compute_badge_ids(self):
        self._compute_from_employee('badge_ids')
