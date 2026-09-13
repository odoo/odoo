from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    invoice_policy = fields.Boolean(help="Timesheets taken when invoicing time spent")
