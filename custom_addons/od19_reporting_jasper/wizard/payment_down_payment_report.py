# -*- coding: utf-8 -*-
"""R-AC-005 Payment Down Payment report.

Odoo 19 port of the legacy ``dtr_accounting_report`` report
``payment_down_payment_report``.  It lists inbound/outbound payments that are
linked to a down-payment invoice and embeds the
``payment_down_payment_cheque_report`` subreport (cheque details per payment).

Odoo 19 adaptations applied to ``jrxml/payment_down_payment_report.jrxml``:

* ``dtr_account_invoice_payment_method`` -> ``account_payment_method_line``
  (``pay.payment_method_line_id``).
* ``account_move.payment_id`` was removed; the payment move is reached through
  ``account_move.id = account_payment.move_id``.
* ``account_move.voucher_running_no`` -> ``account_payment.od19_voucher_no``;
  ``amount_wht`` -> ``od19_wht_amount``, ``amount_fee`` -> ``fee_amount`` and
  ``amount_with_fee`` -> ``amount + fee_amount``.
* the legacy invoice relation tables (``account_move_account_payment_rel`` /
  ``account_payment_account_billing_rel``) were replaced by the standard
  ``account_move__account_payment`` link (``invoice_id`` / ``payment_id``); the
  billing-rel branch no longer exists in Odoo 19.
* ``inv.order_type = 'down_payment'`` -> ``inv.od19_downpayment_source IS NOT
  NULL`` (the stored down-payment marker from ``od19_sale_wizards``);
  ``inv.order_type`` and ``account_move.od19_is_downpayment`` are not stored
  columns and cannot be used in SQL.
* ``res_partner.display_name`` -> ``res_partner.name``; the partner domain uses
  ``customer_rank`` / ``supplier_rank``.

The legacy template computed ``p_From_Date_Text`` / ``p_To_Date_Text`` by
comparing ``date_type`` against ``'th_TH'`` (which never matches), so the BE
offset was silently ignored; it now follows ``date_type`` like every other
ported form.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class PaymentDownPaymentReport(models.TransientModel):
    _name = "payment.down.payment.report"
    _description = "Payment DownPayment Report"
    _inherit = "od19.jasper.report"

    name = fields.Char()
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
        default="thai",
    )
    p_Order_By = fields.Selection(
        [("date", "Document Date"), ("doc", "Document No")],
        string="Order By",
        required=True,
        default="date",
    )
    p_Group_By = fields.Selection(
        [
            ("partner", "Customer / Vendor"),
            ("journal", "Journal"),
            ("payment_method", "Payment Method"),
        ],
        string="Group By",
        required=True,
        default="partner",
    )
    p_Journal = fields.Many2many(
        "account.journal",
        relation="od19_payment_down_payment_report_journal_rel",
        string="Journal (Specific)",
    )
    p_Partner = fields.Many2many(
        "res.partner",
        relation="od19_payment_down_payment_report_partner_rel",
        string="Partner (Specific)",
        domain=["|", ("customer_rank", ">", 0), ("supplier_rank", ">", 0)],
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
        self.name = "Payment Down Payment Report"
        company = self.company_id or self.env.company
        p_Where = (
            "WHERE pay.company_id = {0} AND (pay.payment_type = 'inbound' OR "
            "pay.payment_type = 'outbound') AND am.state in ('posted')"
        ).format(company.id)
        p_Journal = "ทั้งหมด" if self.p_language == "thai" else "All"
        p_Partner = "ทั้งหมด" if self.p_language == "thai" else "All"
        if self.p_Journal:
            p_Where += " AND am.journal_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Journal)
            )
            p_Journal = ", ".join(i.name for i in self.p_Journal)
        if self.p_Partner:
            p_Where += " AND pay.partner_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Partner)
            )
            p_Partner = ", ".join(i.display_name for i in self.p_Partner)

        p_Order_By = ""
        if self.p_Order_By == "doc":
            if self.p_Group_By == "partner":
                p_Order_By = "ORDER BY pay.partner_id, am.name"
            elif self.p_Group_By == "journal":
                p_Order_By = "ORDER BY am.journal_id, am.name"
            elif self.p_Group_By == "payment_method":
                p_Order_By = "ORDER BY pay.payment_method_line_id, am.name"
        elif self.p_Order_By == "date":
            if self.p_Group_By == "partner":
                p_Order_By = "ORDER BY pay.partner_id, am.date"
            elif self.p_Group_By == "journal":
                p_Order_By = "ORDER BY am.journal_id, am.date"
            elif self.p_Group_By == "payment_method":
                p_Order_By = "ORDER BY pay.payment_method_line_id, am.date"

        p_Order_By_Display = ""
        p_Group_By_Display = ""
        if self.p_language == "thai":
            if self.p_Group_By == "partner":
                p_Group_By_Display = "คู่ค้า"
            elif self.p_Group_By == "journal":
                p_Group_By_Display = "สมุดรายวัน"
            elif self.p_Group_By == "payment_method":
                p_Group_By_Display = "วิธีชำระเงิน"

            if self.p_Order_By == "date":
                p_Order_By_Display = "วันที่เอกสาร"
            elif self.p_Order_By == "doc":
                p_Order_By_Display = "เลขที่เอกสาร"
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
                "p_Partner": p_Partner,
                "p_From_Date": str(self.p_From_Date),
                "p_To_Date": str(self.p_To_Date),
                "p_From_Date_Text": self._legacy_date_text(self.p_From_Date),
                "p_To_Date_Text": self._legacy_date_text(self.p_To_Date),
            }
        )
        return parameters
