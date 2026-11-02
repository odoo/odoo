# -*- coding: utf-8 -*-
"""R-AC-004 Prepayment Condition report.

Odoo 19 port of the legacy ``dtr_accounting_report`` report
``prepayment_condition_report``.  It lists the vendor bills attached to vendor
``account.billing`` documents (ใบรับวางบิล) for a prepayment-date /
actual-due-date range, grouped per prepayment document.

Odoo 19 adaptations applied to ``jrxml/prepayment_condition_report.jrxml``:

* ``dtr_account_prepayment`` -> OCA ``account_billing`` (``bill_type='in_invoice'``);
  ``bill.number`` -> ``bill.name``, ``bill.bill_date`` -> ``bill.date``,
  ``bill.actual_due_date`` -> ``bill.threshold_date``, ``bill.notes`` ->
  ``bill.narration``.
* the invoice relation ``account_move_dtr_account_prepayment_rel`` is replaced
  by the OCA ``account_billing_line`` (``billing_id`` / ``move_id``).
* ``dtr_account_invoice_payment_method`` (removed) -> the invoice's
  ``preferred_payment_method_line_id`` (``account_payment_method_line``).
* ``res_partner.display_name`` -> ``res_partner.name``; the vendor domain now
  uses ``supplier_rank``.

The legacy template carries the internal report name ``billing_condition_report``;
that quirk is preserved byte-identically (only the ``<queryString>`` changed).
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class PrepaymentConditionReport(models.TransientModel):
    _name = "prepayment.condition.report"
    _description = "Prepayment Condition Report"
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
    p_Prepayment_Start_Date = fields.Date(
        string="Prepayment Start Date",
        required=True,
        default=lambda self: self.default_start_date(),
    )
    p_Prepayment_End_Date = fields.Date(
        string="Prepayment End Date",
        required=True,
        default=fields.Date.context_today,
    )
    p_Act_Start_Date = fields.Date(
        string="Actual Due Start Date",
        required=True,
        default=lambda self: self.default_start_date(),
    )
    p_Act_End_Date = fields.Date(
        string="Actual Due End Date",
        required=True,
        default=fields.Date.context_today,
    )
    p_Vendor = fields.Many2many(
        "res.partner",
        relation="od19_prepayment_condition_report_vendor_rel",
        string="Vendor (Specific)",
        domain=[("supplier_rank", ">", 0)],
    )
    p_Payment_Method = fields.Many2many(
        "account.payment.method.line",
        relation="od19_prepayment_condition_report_payment_method_rel",
        string="Payment Method (Specific)",
    )
    p_Currency = fields.Many2many(
        "res.currency",
        relation="od19_prepayment_condition_report_currency_rel",
        string="Currency (Specific)",
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
        return fields.Date.context_today(self).replace(day=1)

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Prepayment Report"
        company = self.company_id or self.env.company
        p_Where = (
            "WHERE bill.state in ('done', 'open') AND bill.bill_type = 'in_invoice' "
            "AND date(bill.date) >= '{0}' AND date(bill.date) <= '{1}' "
            "AND date(bill.threshold_date) >= '{2}' AND date(bill.threshold_date) <= '{3}' "
            "AND bill.company_id = {4}"
        ).format(
            self.p_Prepayment_Start_Date,
            self.p_Prepayment_End_Date,
            self.p_Act_Start_Date,
            self.p_Act_End_Date,
            company.id,
        )
        p_Vendor = "ทั้งหมด" if self.p_language == "thai" else "All"
        p_Payment_Method = "ทั้งหมด" if self.p_language == "thai" else "All"
        p_Currency = "ทั้งหมด" if self.p_language == "thai" else "All"
        if self.p_Vendor:
            p_Where += " AND bill.partner_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Vendor)
            )
            p_Vendor = ", ".join(i.display_name for i in self.p_Vendor)
        if self.p_Payment_Method:
            p_Where += " AND inv.preferred_payment_method_line_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Payment_Method)
            )
            p_Payment_Method = ", ".join(i.name for i in self.p_Payment_Method)
        if self.p_Currency:
            p_Where += " AND bill.currency_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Currency)
            )
            p_Currency = ", ".join(i.name for i in self.p_Currency)

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_Where": p_Where,
                "p_Prepayment_Start_Date": str(self.p_Prepayment_Start_Date),
                "p_Prepayment_End_Date": str(self.p_Prepayment_End_Date),
                "p_Act_Start_Date": str(self.p_Act_Start_Date),
                "p_Act_End_Date": str(self.p_Act_End_Date),
                "p_Vendor": p_Vendor,
                "p_Payment_Method": p_Payment_Method,
                "p_Currency": p_Currency,
            }
        )
        return parameters
