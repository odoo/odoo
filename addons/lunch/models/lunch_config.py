from odoo import fields, models


class LunchConfig(models.Model):
    _name = "lunch.config"
    _description = "A company's lunch configuration"
    _inherit = ["mixin.company.config"]

    lunch_minimum_threshold = fields.Float()
    lunch_notify_message = fields.Html(
        translate=True,
        default="""Your lunch has been delivered.
Enjoy your meal!""",
    )
