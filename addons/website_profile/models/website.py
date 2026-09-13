from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    karma_profile_min = fields.Integer(
        string="Minimal karma to see other user's profile",
        default=150,
    )
