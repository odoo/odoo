# -*- coding: utf-8 -*-
"""Credit/Debit Note Report (R-AC-009).

Odoo 19 port of the legacy ``dtr_accounting_report`` wizard.  It is menu-driven
(not bound to a document) and reuses the shared engine
:class:`od19.jasper.report`.

Odoo 19 adaptations applied to ``jrxml/credit_debit_note_report.jrxml``:

* ``res_partner.display_name`` no longer exists as a stored column, so the
  partner name comes from ``res_partner.name``.
* ``account_move.actual_due_date`` was renamed ``od19_actual_due_date`` (the
  field is still exposed as ``actual_due_date`` in the report parameter and
  ordering).
* The custom ``dtr_account_prepayment`` / ``dtr_account_billing`` tables were
  dropped; ``bill_no`` is resolved from the standard ``account_billing`` model.
* The legacy ``_compute_default_date_type`` / ``_compute_default_date_format``
  helpers resolved ``dtr.report.base`` records that do not exist in Odoo 19 and
  are replaced by static defaults; the ``dtr_accounting_report`` allow-check
  (``err_msg``) was dropped with the same rationale.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class CreditDebitNoteReport(models.TransientModel):
    _name = "credit.debit.note.report"
    _description = "Credit/Debit Note Report"
    _inherit = "od19.jasper.report"

    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
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
    report_type = fields.Selection(
        [("cn", "Credit Note"), ("dn", "Debit Note")],
        string="Report Type",
        required=True,
        default="cn",
    )
    p_From_Date = fields.Date(
        string="From Date", required=True, default=fields.Date.context_today
    )
    p_To_Date = fields.Date(
        string="To Date", required=True, default=fields.Date.context_today
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

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        if self.report_type == "cn":
            self.name = "Credit Note Report"
            p_Where = "WHERE (inv.dncn = 'cn' OR inv.move_type = 'in_refund')"
        else:
            self.name = "Debit Note Report"
            p_Where = "WHERE (inv.dncn = 'dn' AND inv.move_type = 'out_invoice')"

        p_Where += " AND inv.state in ('posted') AND inv.company_id = {0}".format(
            self.company_id.id
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

        year_add = 543 if self.date_type == "BE" else 0
        dt_from = fields.Date.from_string(self.p_From_Date)
        date_from_text = "{0:02d}-{1:02d}-{2:d}".format(
            dt_from.day, dt_from.month, dt_from.year + year_add
        )
        dt_to = fields.Date.from_string(self.p_To_Date)
        date_to_text = "{0:02d}-{1:02d}-{2:d}".format(
            dt_to.day, dt_to.month, dt_to.year + year_add
        )

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_Where": p_Where,
                "p_Order_By": p_Order_By,
                "p_Order_By_Display": p_Order_By_Display,
                "p_Group_By": self.p_Group_By,
                "p_Group_By_Display": p_Group_By_Display,
                "p_From_Date": str(self.p_From_Date),
                "p_To_Date": str(self.p_To_Date),
                "p_From_Date_Text": date_from_text,
                "p_To_Date_Text": date_to_text,
            }
        )
        return parameters
