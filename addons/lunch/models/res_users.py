from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    last_lunch_location_id = fields.Many2one(
        comodel_name="lunch.location",
        copy=False,
        groups="lunch.group_lunch_user",
    )
