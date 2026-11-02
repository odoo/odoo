# -*- coding: utf-8 -*-
"""Inventory Valuation (มูลค่าคงเหลือ) - port of the legacy
``dtr_stock_report`` report ``F-IV-003`` (``inventory.valuation.report``).

The ``.jrxml`` (``jrxml/inventory_valuation_report.jrxml``) is shipped
unchanged except for the ``queryString`` which now targets the Odoo 19 schema
(``stock.valuation.layer`` is replaced by ``stock_move``).
"""
from odoo import _, fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class InventoryValuationReport(models.TransientModel):
    _name = "inventory.valuation.report"
    _description = "Inventory Valuation"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Inventory Valuation Report")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
        default="thai",
        required=True,
    )
    date_type = fields.Selection(
        [("AD", "AD"), ("BE", "BE")],
        string="Date Type",
        default="AD",
        required=True,
        help="AD = คริสตศักราช\nBE = พุทธศักราช",
    )
    date_format = fields.Selection(
        [(value, value) for value in DATE_FORMATS],
        string="Date Format",
        default="dd-MM-yyyy",
        required=True,
    )
    p_EName = fields.Boolean(string="Show Employee Name", default=True)
    p_ESignature = fields.Boolean(string="Show Signature", default=True)

    p_Product = fields.Many2many(
        "product.product",
        "product_product_inventory_valuation_report",
        string="Product (Specific)",
        domain="[('is_storable', '=', True)]",
    )
    p_Location = fields.Many2many(
        "stock.location",
        "stock_location_inventory_valuation_report",
        string="Location (Specific)",
        domain="[('usage', '=', 'internal')]",
    )
    p_Lot = fields.Many2many(
        "stock.lot",
        "stock_lot_inventory_valuation_report",
        string="Lot (Specific)",
    )
    date = fields.Date(
        string="At Date", required=True, default=fields.Date.today
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Inventory Valuation Report"
        return {
            "p_Path": self._legacy_filestore_path(),
            "p_User_ID": str(self.env.user.id),
            "p_ISO": self.iso_no or "",
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_DateFormat": str(self.date_format),
            "p_language": str(self.p_language),
            "p_locale": self._legacy_locale(),
            "p_To_Date": str(self.date),
            "p_WhereProduct": " AND mv.product_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Product)
            )
            if self.p_Product
            else "",
            "p_WhereLocation": " AND loc_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Location)
            )
            if self.p_Location
            else "",
            "p_WhereLot": " AND mv.lot_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Lot)
            )
            if self.p_Lot
            else "",
            "p_CompanyId": str(self.company_id.id),
        }
