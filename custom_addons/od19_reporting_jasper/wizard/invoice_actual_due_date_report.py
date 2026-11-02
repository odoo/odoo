# -*- coding: utf-8 -*-
"""R-AC-008 Invoice Actual Due Date.

Odoo 19 port of the legacy ``dtr_accounting_report`` wizard.  It is menu-driven
(not bound to a document) and reuses the shared engine
:class:`od19.jasper.report`.

Odoo 19 adaptations applied to ``jrxml/invoice_actual_due_date_report.jrxml``:

* ``account_move.actual_due_date`` was renamed ``od19_actual_due_date``, so the
  ``p_Where`` date-range filter targets ``date(inv.od19_actual_due_date)``.
* ``res_partner.display_name`` no longer exists as a stored column, so the
  partner name comes from ``res_partner.name``.
* The custom ``dtr_account_prepayment`` / ``dtr_account_billing`` tables were
  dropped; ``bill_no`` is resolved from the standard ``account_billing`` model.
* The legacy ``_compute_default_date_type`` / ``_compute_default_date_format``
  helpers resolved ``dtr.report.base`` records that do not exist in Odoo 19 and
  are replaced by static defaults; the ``dtr_accounting_report`` allow-check
  (``err_msg``) was dropped with the same rationale.
"""
from datetime import date

from odoo import fields, models

from .invoice_form import DATE_FORMATS


class InvoiceActualDueDateReport(models.TransientModel):
    _name = "invoice.actual.due.date.report"
    _description = "Invoice Actual Due Date Report"
    _inherit = "od19.jasper.report"

    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    p_Act_Start_Date = fields.Date(
        string="Actual Due Start Date",
        required=True,
        default=lambda self: self.default_start_date(),
    )
    p_Act_End_Date = fields.Date(
        string="Actual Due End Date",
        required=True,
        default=fields.Date.today,
    )
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
        default="thai",
        required=True,
    )
    p_Order_By = fields.Selection(
        [("name", "Invoice No."), ("invoice_date", "Invoice Date"), ("actual_due_date", "Due Date")],
        string="Order By",
        required=True,
        default="name",
    )
    p_Group_By = fields.Selection(
        [("Partner", "Partner"), ("Salesperson", "Salesperson")],
        string="Group By",
        required=True,
        default="Partner",
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

    def default_start_date(self):
        today = fields.Date.from_string(fields.Date.today())
        return date(today.year, today.month, 1)

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Invoice Actual Due Date Report"
        p_Where = (
            "WHERE (inv.dncn = '' OR inv.dncn is null) AND inv.state in ('posted') "
            "AND inv.move_type in ('out_invoice', 'in_invoice')"
            "AND date(inv.od19_actual_due_date) >= '" + str(self.p_Act_Start_Date)
            + "' AND date(inv.od19_actual_due_date) <= '" + str(self.p_Act_End_Date)
            + "' AND inv.company_id = " + str(self.company_id.id)
        )

        p_Order_By = (
            "ORDER BY inv.partner_id"
            if self.p_Group_By == "Partner"
            else "ORDER BY inv.invoice_user_id"
        )
        p_Order_By_Display = ""
        p_Group_By_Display = ""
        if self.p_Order_By:
            order_field = (
                "od19_actual_due_date"
                if self.p_Order_By == "actual_due_date"
                else self.p_Order_By
            )
            p_Order_By += ",inv.{0}".format(order_field)

        if self.p_language == "thai":
            p_Group_By_Display = "คู่ค้า" if self.p_Group_By == "Partner" else "ผู้ขาย"
            if self.p_Order_By == "name":
                p_Order_By_Display = "เลขที่ใบกำกับภาษี"
            elif self.p_Order_By == "invoice_date":
                p_Order_By_Display = "วันที่ครบกำหนด"
            elif self.p_Order_By == "actual_due_date":
                p_Order_By_Display = "วันที่นัดชำระ"
        else:
            p_Group_By_Display = self.p_Group_By
            p_Order_By_Display = dict(self._fields["p_Order_By"].selection).get(
                self.p_Order_By
            )

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_Where": p_Where,
                "p_Act_Start_Date": str(self.p_Act_Start_Date.strftime("%Y-%m-%d")),
                "p_Act_End_Date": str(self.p_Act_End_Date.strftime("%Y-%m-%d")),
                "p_Order_By": p_Order_By,
                "p_Order_By_Display": p_Order_By_Display,
                "p_Group_By": self.p_Group_By,
                "p_Group_By_Display": p_Group_By_Display,
            }
        )
        return parameters
