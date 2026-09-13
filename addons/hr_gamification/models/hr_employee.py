from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    goal_ids = fields.One2many(
        comodel_name="gamification.goal",
        string="Employee HR Goals",
        compute="_compute_employee_goals",
        groups="hr.group_hr_user",
    )
    badge_ids = fields.One2many(
        comodel_name="gamification.badge.user",
        string="Employee Badges",
        help="All employee badges, linked to the employee either directly or through the user",
        compute="_compute_employee_badges",
    )
    has_badges = fields.Boolean(compute="_compute_employee_badges")
    direct_badge_ids = fields.One2many(
        comodel_name="gamification.badge.user",
        inverse_name="employee_id",
        help="Badges directly linked to the employee",
        groups="hr.group_hr_user",
    )

    @api.depends("user_id.goal_ids.challenge_id.challenge_category")
    def _compute_employee_goals(self):
        goals = self.env["gamification.goal"].search(
            [
                ("user_id", "in", self.user_id.ids),
                ("challenge_id.challenge_category", "=", "hr"),
            ]
        )
        goals_by_user = goals.grouped("user_id")
        for employee in self:
            employee.goal_ids = goals_by_user.get(employee.user_id, goals.browse())

    @api.depends("direct_badge_ids", "user_id.badge_ids.employee_id")
    def _compute_employee_badges(self):
        badges = self.env["gamification.badge.user"].search(
            [
                "|",
                ("employee_id", "in", self.ids),
                "&",
                ("employee_id", "=", False),
                ("user_id", "in", self.user_id.ids),
            ]
        )
        direct = badges.grouped("employee_id")
        inherited = badges.filtered(lambda badge: not badge.employee_id).grouped(
            "user_id"
        )
        for employee in self:
            employee_badges = direct.get(employee, badges.browse())
            if employee.user_id:
                employee_badges |= inherited.get(employee.user_id, badges.browse())
                employee_badges = badges & employee_badges
            employee.has_badges = bool(employee_badges)
            employee.badge_ids = employee_badges
