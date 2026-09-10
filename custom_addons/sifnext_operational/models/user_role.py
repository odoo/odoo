from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    sifnext_active_role = fields.Selection(
        [
            ("user", "Operational User"),
            ("ga", "General Affair"),
        ],
        string="SIFNEXT Active Role",
        default="user",
        required=True,
    )