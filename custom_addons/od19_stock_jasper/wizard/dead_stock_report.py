# -*- coding: utf-8 -*-
"""Dead Stock (สินค้าไม่เคลื่อนไหว) - port of the legacy ``dtr_stock_report``
report ``F-IV-008`` (``dead.stock.report``).

The ``.jrxml`` (``jrxml/dead_stock_report.jrxml``) is shipped unchanged except
for the ``queryString`` which now targets the Odoo 19 schema: the remaining
quantity / value are recomputed from ``stock_quant`` because
``stock.valuation.layer`` no longer exists.
"""
from datetime import timedelta

from odoo import _, fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class DeadStockReport(models.TransientModel):
    _name = "dead.stock.report"
    _description = "Dead Stock"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Dead Stock Report")
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
    p_Print_By = fields.Char(
        string="Printed By", default=lambda self: self.env.user.name
    )

    p_location = fields.Many2many(
        "stock.location",
        "stock_location_dead_stock_report",
        string="Location (Specific)",
    )
    p_days = fields.Integer(string="Days of Range", required=True, default=30)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Dead Stock Report"
        date_filter = fields.Date.today() + timedelta(days=-self.p_days)
        p_where = (
            "where a.company_id = "
            + str(self.company_id.id)
            + " and date(a.last_outgoing_date) is null or "
            "date(a.last_outgoing_date) <= '"
            + str(date_filter)
            + "' and a.first_incoming_date is not null"
        )
        p_location_src_id = ""
        if self.p_location:
            p_location_src_id += " and q.location_id in ({0})".format(
                ", ".join(str(i) for i in self.p_location.ids)
            )
        if self.p_location:
            location_text = ", ".join(
                str(i.complete_name) for i in self.p_location
            )
        else:
            location_text = "ทั้งหมด" if self.p_language == "thai" else "All"
        return {
            "p_Print_By": self.p_Print_By or "",
            "p_DateFormat": str(self.date_format),
            "p_language": str(self.p_language),
            "p_locale": self._legacy_locale(),
            "p_location": location_text,
            "p_days": str(self.p_days),
            "p_Where": p_where,
            "p_location_src_id": p_location_src_id,
        }
