# -*- coding: utf-8 -*-
"""Delivery Order report (ใบส่งของ - รายงาน) - port of the legacy
``dtr_stock_report`` report ``delivery_order_report``.

Reached from ``Stock > any transfer > Print > Delivery Order Report``; the
selected ``stock.picking`` ids are handed to the template through the legacy
``ids`` SQL fragment.  The ``.jrxml`` (``jrxml/delivery_order_report.jrxml``)
is shipped unchanged except for the ``queryString`` which now targets the
Odoo 19 schema.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class DeliveryOrderReport(models.TransientModel):
    _name = "delivery.order.report"
    _description = "Delivery Order Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Delivery Order Report")
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
            ids, "stock.picking", "Delivery Order Report"
        )
        return {
            "ids": self._legacy_ids_where("sp"),
        }
