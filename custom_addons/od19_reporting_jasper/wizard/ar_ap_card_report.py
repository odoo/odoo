# -*- coding: utf-8 -*-
"""R-AC-010 AR/AP Card.

Odoo 19 port of the legacy ``dtr_accounting_report`` report
``ar_ap_card_report``.  Like the AR/AP Aging form the wizard is opened from the
Accounting > Reporting menu (it is not bound to a document), so it selects its
own scope (company, period, account type, accounts, partners).

Odoo 19 adaptations applied to ``jrxml/ar_ap_card_report.jrxml``:

* ``account_account_type`` was dropped after Odoo 15, so the
  ``aa.user_type_id -> account_account_type.type`` join is replaced by the
  ``account_account.account_type`` selection (``asset_receivable`` /
  ``liability_payable``).
* ``res_partner.customer`` / ``res_partner.supplier`` are replaced by
  ``customer_rank`` / ``supplier_rank``.
* ``account_move.payment_id`` was removed; the payment is now reached through
  the reverse join ``account_payment.move_id = account_move.id``.
* ``account_move.voucher_running_no`` -> ``account_payment.od19_voucher_no`` and
  the stored ``actual_due_date`` / ``exchange_rate`` columns are gone, so the
  due date falls back to ``invoice_date_due`` and the rate is looked up in
  ``res_currency_rate``.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class ArApCardReport(models.TransientModel):
    _name = "ar.ap.card.report"
    _description = "AR/AP Card Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="AR/AP Card")
    report_name = fields.Char(default="รายงานการ์ดลูกหนี้/เจ้าหนี้")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    start_date = fields.Date(
        string="Start Date", required=True, default=fields.Date.context_today
    )
    p_As_Date = fields.Date(
        string="End Date", required=True, default=fields.Date.context_today
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
    p_Type = fields.Selection(
        [("ar", "Account Receivable"), ("ap", "Account Payable")],
        string="Account Type",
        default="ar",
        required=True,
    )
    account_ids = fields.Many2many(
        "account.account",
        relation="od19_ar_ap_card_report_account_rel",
        string="Account Code",
    )
    customer_ids = fields.Many2many(
        "res.partner",
        relation="od19_ar_ap_card_report_customer_rel",
        string="Customer",
        domain=[("customer_rank", ">", 0)],
    )
    vendor_ids = fields.Many2many(
        "res.partner",
        relation="od19_ar_ap_card_report_vendor_rel",
        string="Vendor",
        domain=[("supplier_rank", ">", 0)],
    )

    def _legacy_date_text(self, value):
        """``23-10-2569`` (BE) / ``23-10-2026`` (AD) for one date value."""
        year_add = 543 if self.date_type == "BE" else 0
        return "{0:02d}-{1:02d}-{2:d}".format(
            value.day, value.month, value.year + year_add
        )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        partner_ids = self.customer_ids if self.p_Type == "ar" else self.vendor_ids
        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_AccountCodeText": ", ".join(self.account_ids.mapped("code"))
                if self.account_ids
                else "",
                "p_DateText": "ตั้งแต่วันที่ %s ถึง %s"
                % (
                    self._legacy_date_text(self.start_date),
                    self._legacy_date_text(self.p_As_Date),
                ),
                "start_date": str(self.start_date),
                "p_As_Date": str(self.p_As_Date),
                "p_Type": self.p_Type,
                "p_Print_By": self._legacy_print_by(),
                "company_id": "%s" % self.company_id.id,
                "company_name": self.company_id.name,
                "account_ids": ("array%s" % self.account_ids.ids)
                if self.account_ids
                else "null",
                "partner_ids": ("array%s" % partner_ids.ids)
                if partner_ids
                else "null",
                "partner_type": "customer" if self.p_Type == "ar" else "supplier",
            }
        )
        return parameters
