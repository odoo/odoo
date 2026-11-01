# -*- coding: utf-8 -*-
"""Customer Invoice / Tax Invoice form (ใบกำกับภาษี).

Odoo 19 port of the legacy ``dtr_invoicing_report`` wizard
``tax_invoice_report``.  It is bound to ``account.move`` (opened from the
document "Print" menu) and prints the selected customer invoices.

Odoo 19 adaptations applied to ``jrxml/tax_invoice_report.jrxml``:

* ``res_partner.display_name`` -> ``res_partner.name``.
* ``res_company.fax`` / ``res_company.branch_code`` no longer exist; both are
  read from the company partner (``cpartner.fax`` / ``cpartner.branch_code``).
* The legacy ``dtr_customer_selling_area`` table (and
  ``res_partner.dtr_selling_area``) has no Odoo 19 equivalent, so the printout
  keeps an empty ``salearea_name``.
* ``account_move_line.discount_type`` / ``is_trade_discount`` /
  ``exclude_from_invoice_tab`` were dropped by Odoo.  The printed discount is
  taken from the standard ``discount`` percentage and the line filter uses
  ``display_type = 'product'``.
* ``account_move.amount_untaxed_before_trade_discount`` /
  ``amount_trade_discount`` no longer exist; the trade discount prints as ``0``
  and the untaxed amount uses ``amount_untaxed``.
"""
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class TaxInvoiceReport(models.TransientModel):
    _name = "tax.invoice.report"
    _description = "Customer Invoice Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Invoice")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        return {
            "ids": self._legacy_ids_where("inv"),
            "iscopy": self._legacy_is_copy(),
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        invoices = self.env["account.move"].browse(
            self.env.context.get("active_ids") or []
        )
        for invoice in invoices:
            if invoice.move_type != "out_invoice":
                raise ValidationError(_("Document is not Customer Invoice."))
            if invoice.state != "posted":
                raise ValidationError(_("Invoice(s) is not ready to Print."))
        return super().show_report("Customer Invoice(s)")
