# -*- coding: utf-8 -*-
"""R-AC-001 Payment Outbound report.

Odoo 19 port of the legacy ``dtr_accounting_report`` report
``payment_outbound_report``.  It lists posted outbound payments for a period
together with the cheque used to pay each vendor.

Odoo 19 adaptations applied to ``jrxml/payment_outbound_report.jrxml``:

* ``dtr_account_invoice_payment_method`` -> ``account_payment_method_line``
  (``pay.payment_method_line_id``).
* ``account_move.payment_id`` was removed; the payment move is reached through
  ``account_move.id = account_payment.move_id``.
* ``account_move.voucher_running_no`` -> ``account_payment.od19_voucher_no``;
  the legacy ``amount_wht`` / ``amount_fee`` / ``amount_with_fee`` columns are
  gone and map to ``od19_wht_amount`` / ``fee_amount`` (+ amount).
* ``dtr_cheque_leaf`` -> ``account_cheque`` (``cheque_paid_id``), whose date
  column is ``cheque_date``.
* the legacy invoice relation tables were replaced by the standard
  ``account_move__account_payment`` link.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class PaymentOutboundReport(models.TransientModel):
    _name = "payment.outbound.report"
    _description = "Payment Outbound Report"
    _inherit = "od19.jasper.report"

    name = fields.Char()
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
        default="thai",
    )
    p_Order_By = fields.Selection(
        [("payment_date", "Payment Date"), ("payment_no", "Payment No")],
        string="Order By",
        required=True,
        default="payment_no",
    )
    p_Group_By = fields.Selection(
        [
            ("vendor", "Vendor"),
            ("journal", "Journal"),
            ("payment_method", "Payment Method"),
        ],
        string="Group By",
        required=True,
        default="vendor",
    )
    p_Journal = fields.Many2many(
        "account.journal",
        relation="od19_payment_outbound_report_journal_rel",
        string="Journal (Specific)",
    )
    p_Vendor = fields.Many2many(
        "res.partner",
        relation="od19_payment_outbound_report_vendor_rel",
        string="Vendor (Specific)",
        domain=[("supplier_rank", ">", 0)],
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

    def _legacy_date_text(self, value):
        """``23-10-2569`` (BE) / ``23-10-2026`` (AD) for one date value."""
        year_add = 543 if self.date_type == "BE" else 0
        return "{0:02d}-{1:02d}-{2:d}".format(
            value.day, value.month, value.year + year_add
        )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Payment Outbound Report"
        p_Where = (
            "WHERE pay.company_id = {0} AND pay.payment_type = 'outbound' "
            "AND am.state in ('posted') AND pay2.date BETWEEN '{1}' AND '{2}'"
        ).format(self.env.company.id, self.p_From_Date, self.p_To_Date)
        p_Journal = "ทั้งหมด" if self.p_language == "thai" else "All"
        p_Vendor = "ทั้งหมด" if self.p_language == "thai" else "All"
        if self.p_Journal:
            p_Where += " AND am.journal_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Journal)
            )
            p_Journal = ", ".join(i.name for i in self.p_Journal)
        if self.p_Vendor:
            p_Where += " AND pay.partner_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Vendor)
            )
            p_Vendor = ", ".join(i.display_name for i in self.p_Vendor)

        p_Order_By = ""
        if self.p_Order_By == "payment_no":
            if self.p_Group_By == "vendor":
                p_Order_By = "ORDER BY pay.partner_id, am.name"
            elif self.p_Group_By == "journal":
                p_Order_By = "ORDER BY am.journal_id, am.name"
            elif self.p_Group_By == "payment_method":
                p_Order_By = "ORDER BY pay.payment_method_line_id, am.name"
        elif self.p_Order_By == "payment_date":
            if self.p_Group_By == "vendor":
                p_Order_By = "ORDER BY pay.partner_id, am.date"
            elif self.p_Group_By == "journal":
                p_Order_By = "ORDER BY am.journal_id, am.date"
            elif self.p_Group_By == "payment_method":
                p_Order_By = "ORDER BY pay.payment_method_line_id, am.date"

        p_Order_By_Display = ""
        p_Group_By_Display = ""
        if self.p_language == "thai":
            if self.p_Group_By == "vendor":
                p_Group_By_Display = "ผู้ขาย"
            elif self.p_Group_By == "journal":
                p_Group_By_Display = "สมุดรายวัน"
            elif self.p_Group_By == "payment_method":
                p_Group_By_Display = "วิธีชำระเงิน"

            if self.p_Order_By == "payment_date":
                p_Order_By_Display = "วันที่จ่ายเงิน"
            elif self.p_Order_By == "payment_no":
                p_Order_By_Display = "เลขที่จ่าย"
        else:
            p_Group_By_Display = dict(self._fields["p_Group_By"].selection).get(
                self.p_Group_By
            )
            p_Order_By_Display = dict(self._fields["p_Order_By"].selection).get(
                self.p_Order_By
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
                "p_Journal": p_Journal,
                "p_Vendor": p_Vendor,
                "p_From_Date": str(self.p_From_Date),
                "p_To_Date": str(self.p_To_Date),
                "p_From_Date_Text": self._legacy_date_text(self.p_From_Date),
                "p_To_Date_Text": self._legacy_date_text(self.p_To_Date),
            }
        )
        return parameters
