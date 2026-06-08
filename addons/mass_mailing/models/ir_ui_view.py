from odoo import fields, models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    technical_usage = fields.Selection(selection_add=[("mass_mailing", "Mass Mailing Technical")])
