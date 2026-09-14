from odoo import models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    def _get_client_button_types(self, view_type):
        types = super()._get_client_button_types(view_type)
        if view_type == "form":
            types.add("team_event")
        return types
