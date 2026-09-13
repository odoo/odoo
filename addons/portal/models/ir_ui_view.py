from odoo import fields, models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    customize_show = fields.Boolean(
        string="Show As Optional Inherit",
        default=False,
        help="When set, the website editor surfaces this view as a user-togglable "
        "inherited variant of its parent (used by the Customize panel).",
    )
