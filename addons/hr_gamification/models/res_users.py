from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    goal_ids = fields.One2many(
        comodel_name="gamification.goal",
        inverse_name="user_id",
    )
    badge_ids = fields.One2many(
        comodel_name="gamification.badge.user",
        inverse_name="user_id",
    )
