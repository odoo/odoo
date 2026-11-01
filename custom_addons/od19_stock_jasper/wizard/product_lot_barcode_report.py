# -*- coding: utf-8 -*-
"""LOT / S/N Barcode label (ป้ายบาร์โค้ดล็อต) - port of the legacy
``dtr_stock_form`` report ``F-IV-010`` (``product.lot.barcode.report``).

Reached from ``Inventory > Products > Lots/Serial Numbers > Print`` and always
prints in English.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductLotBarcodeReport(models.TransientModel):
    _name = "product.lot.barcode.report"
    _description = "LOT or S/N Barcode"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="LOT or S/N Barcode")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )
    p_Print = fields.Integer(string="Number to print", required=True, default=1)

    def _legacy_active_ids(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        return ids

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        self.name = "LOT or S/N Barcode"
        company = self.env.company
        name_en = getattr(company, "name_en", False) or ""
        return {
            "p_Where": "WHERE pd.id in ({0})".format(
                ", ".join(str(i) for i in ids)
            ),
            "p_Print": str(self.p_Print),
            "p_Company_Name": str(name_en) if name_en else "",
            "p_Currency": str(company.currency_id.name),
        }

    def get_locale(self):
        return "en_EN"
