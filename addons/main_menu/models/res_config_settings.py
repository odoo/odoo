from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    show_widgets = fields.Boolean(related="company_id.show_widgets", readonly=False)
