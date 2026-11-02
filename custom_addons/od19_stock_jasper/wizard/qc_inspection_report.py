# -*- coding: utf-8 -*-
"""QC Inspection report (ใบตรวจสอบคุณภาพ) - port of the legacy
``dtr_stock_form`` report ``qc_inspection_report``.

Re-targeted onto the Odoo 19 model ``od19.qc.inspection`` (module
``od19_quality_control``): the legacy ``dtr_quality_controls`` table no longer
exists.  The ``.jrxml`` (``jrxml/qc_inspection_report.jrxml``) is shipped
unchanged except for the ``queryString`` which now targets the Odoo 19 schema.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class QcInspectionReport(models.TransientModel):
    _name = "qc.inspection.report"
    _description = "QC Inspection"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="QC Inspection")
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
    p_Company_No = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    def _legacy_receive_no(self):
        """Legacy ``p_Receive_No`` fragment, e.g. ``WHERE qc.name in ('QC00001')``."""
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        inspections = self.env["od19.qc.inspection"].browse(ids)
        names = ", ".join(
            "'%s'" % name for name in inspections.mapped("name") if name
        )
        return "WHERE qc.name in (%s)" % names

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "QC Inspection"
        return {
            "p_Company_No": str(self.p_Company_No.id),
            "p_Path": self._legacy_filestore_path(),
            "p_ISO": self.iso_no or "",
            "p_Receive_No": self._legacy_receive_no(),
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_language": str(self.p_language),
            "p_DateFormat": str(self.date_format),
            "p_locale": self._legacy_locale(),
        }
