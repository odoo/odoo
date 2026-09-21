from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        res = super().session_info()
        nomenclature = self.env.company.sudo().barcodes_config_id.nomenclature_id
        if not nomenclature.is_gs1_nomenclature:
            return res
        res["gs1_group_separator_encodings"] = nomenclature.gs1_separator_fnc1
        return res
