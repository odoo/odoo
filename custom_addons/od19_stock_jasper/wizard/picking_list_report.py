# -*- coding: utf-8 -*-
"""Picking List (ใบหยิบสินค้า) - port of the legacy ``dtr_stock_report``
report ``picking_list_report``.

Reached from ``Stock > any transfer > Print > Picking List``; the selected
``stock.picking`` ids are handed to the template through the legacy ``ids``
SQL fragment.  The ``.jrxml`` (``jrxml/picking_list_report.jrxml``) is shipped
unchanged except for the ``queryString`` which now targets the Odoo 19 schema.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class PickingListReport(models.TransientModel):
    _name = "picking.list.report"
    _description = "Picking List"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Picking List")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )

    def _legacy_active_ids(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        return ids

    def get_partner_ids_for_send_by_email(self):
        pickings = self.env["stock.picking"].browse(
            self.env.context.get("active_ids", [])
        )
        return pickings.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        self.name = self.get_file_name(
            ids, "stock.picking", "Picking List"
        )
        return {
            "ids": self._legacy_ids_where("sp"),
        }
