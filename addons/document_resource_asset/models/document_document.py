from odoo import models


class DocumentDocument(models.Model):
    _inherit = "document.document"

    def _get_details_panel_res_models(self) -> list[str]:
        return [*super()._get_details_panel_res_models(), "resource.asset"]
