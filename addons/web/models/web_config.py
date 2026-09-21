from odoo import fields, models


class WebConfig(models.Model):
    _name = "web.config"
    _description = "A company's web configuration"
    _inherit = ["mixin.company.config"]

    homemenu_default_config = fields.Json(
        string="Default Home Menu Layout",
        help="The home menu layout a user of this company sees until they "
        "customise their own: the same shape as the user's setting.",
    )
