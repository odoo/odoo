# -*- coding: utf-8 -*-
"""Product QR Code label (ป้าย QR สินค้า) - port of the legacy
``dtr_stock_form`` report ``F-IV-009`` (``product.qrcode.report``).

Reached from ``Inventory > Products > Print > Product QR Code`` and always
prints in English.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductQrcodeReport(models.TransientModel):
    _name = "product.qrcode.report"
    _description = "Product QR Code"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Product QR Code")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )
    p_Show_Price = fields.Boolean(string="Display Sale Price", default=True)
    p_Print = fields.Integer(string="Number to print", required=True, default=1)

    def _legacy_active_ids(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        return ids

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        self.name = "Product QR Code"
        company = self.env.company
        name_en = getattr(company, "name_en", False) or ""
        return {
            "p_Where": "WHERE pt.id in ({0})".format(
                ", ".join(str(i) for i in ids)
            ),
            "p_Print": str(self.p_Print),
            "p_Show_Price": str(self.p_Show_Price),
            "p_Company_Name": str(name_en) if name_en else "",
            "p_Currency": str(company.currency_id.name),
        }

    def get_locale(self):
        return "en_EN"
