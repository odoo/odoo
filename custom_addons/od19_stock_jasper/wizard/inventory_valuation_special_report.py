# -*- coding: utf-8 -*-
"""Product Valuation (Special) (มูลค่าสินค้า - พิเศษ) - port of the legacy
``dtr_stock_report`` report ``F-IV-005``
(``inventory.valuation.special.report``).

The ``.jrxml`` (``jrxml/inventory_valuation_special_report.jrxml``) is shipped
unchanged except for the ``queryString`` which now targets the Odoo 19 schema.
"""
from odoo import _, api, fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class InventoryValuationSpecialReport(models.TransientModel):
    _name = "inventory.valuation.special.report"
    _description = "Product Valuation (Special)"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Product Valuation (Special)")
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

    wh = fields.Many2one("stock.location", string="Location Name")
    p_Product = fields.Many2many(
        "product.product",
        "product_stock_move_valuation_special_report",
        string="Product",
    )
    p_Start_Date = fields.Date(
        string="Start Date", required=True,
        default=lambda self: self._default_start_date(),
    )
    p_To_Date = fields.Date(
        string="To Date", required=True, default=fields.Date.today
    )
    p_Show_BF_Detail = fields.Boolean(string="Show Bring Forward Details")
    p_Show_Transaction_Detail = fields.Boolean(
        string="Show Movement Details", default=True
    )
    p_Internal = fields.Boolean(
        string="Show Price For Internal Transfer", default=True
    )
    p_oder_by = fields.Selection(
        [
            (",sm.id", "Standard (FIFO)"),
            (",sm.date", "Force (Move Date)"),
        ],
        string="Order By",
        required=True,
        default=",sm.id",
    )

    @api.model
    def _default_start_date(self):
        return fields.Date.context_today(self).replace(day=1)

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Product Valuation (Special)"
        companyid = " and sm.company_id = " + str(self.env.company.id)
        whid = 0
        whname = " All Location "
        productlist = " "
        if self.p_Product:
            productlist = " AND pp.id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Product)
            )

        condition = (
            " WHERE sm.state='done' AND date(sml.date) <= '{0}'".format(
                self.p_To_Date
            )
            + productlist
            + companyid
        )
        if self.wh:
            whlist = (
                " WHERE sm.state='done' AND sm.location_id = "
                + str(self.wh.id)
                + " AND date(sml.date) <= '"
                + str(self.p_To_Date)
                + "'"
            )
            whlist1 = (
                " OR sm.state='done' AND sm.location_dest_id = "
                + str(self.wh.id)
                + " AND date(sml.date) <= '"
                + str(self.p_To_Date)
                + "'"
            )
            condition = whlist + productlist + whlist1 + productlist + companyid
            whid = self.wh.id
            whname = self.wh.complete_name

        return {
            "p_Start_Date": str(self.p_Start_Date),
            "p_To_Date": str(self.p_To_Date),
            "p_Location_ID": str(whid),
            "p_Location_Name": str(whname),
            "p_Show_BF_Detail": "1" if self.p_Show_BF_Detail else "0",
            "p_Show_Transaction_Detail": (
                "1" if self.p_Show_Transaction_Detail else "0"
            ),
            "p_Internal": "1" if self.p_Internal else "0",
            "p_Where": str(condition),
            "p_oder_by": str(self.p_oder_by),
            "p_Path": self._legacy_filestore_path(),
            "p_User_ID": str(self.env.user.id),
            "p_ISO": self.iso_no or "",
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_DateFormat": str(self.date_format),
            "p_language": str(self.p_language),
            "p_Period_Start": self.p_Start_Date.strftime("%Y-%m-%d"),
            "p_Period_End": self.p_To_Date.strftime("%Y-%m-%d"),
            "p_locale": self._legacy_locale(),
        }
