from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    lunch_minimum_threshold = fields.Float()
    lunch_notify_message = fields.Html(
        translate=True,
        default="""Your lunch has been delivered.
Enjoy your meal!""",
    )
