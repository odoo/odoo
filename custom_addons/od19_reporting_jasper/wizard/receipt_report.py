# -*- coding: utf-8 -*-
"""Customer Receipt report (ใบเสร็จรับเงิน) - multi-payment.

Odoo 19 port of the legacy ``dtr_accounting_report`` report module
(``reports/receipt_report.py``).  Unlike the single-document
``receipt.form`` wizard, this report is opened with many
``account.payment`` records selected (``active_ids``) and prints one receipt
section per payment.

The legacy wizard lived in the ``dtr_accounting_report`` module, which does
not exist in Odoo 19; no ``self.env.ref('dtr_accounting_report.*')`` guard is
kept and the legacy defaults (``date_type="AD"``, ``date_format="dd-MM-yyyy"``)
are fixed values.

Odoo 19 adaptations applied to ``jrxml/receipt_report.jrxml``:

* ``account_move.payment_id`` was removed; the move is reached through
  ``account_payment.move_id``.
* ``account_account_type`` was dropped, so the receivable filter uses
  ``account_account.account_type = 'asset_receivable'``.
* ``pay.payment_date`` -> ``pay.date``, ``pay.amount_net`` -> ``pay.amount``
  and ``pay.user_id`` -> ``pay.create_uid`` (no ``user_id`` column remains on
  ``account_payment``).
* the custom ``dtr_cheque`` table is replaced by ``account_cheque``.
"""
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ReceiptReport(models.TransientModel):
    _name = "receipt.report"
    _description = "Receipt Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Receipt")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))

    def get_partner_ids_for_send_by_email(self):
        payments = self.env["account.payment"].browse(
            self.env.context.get("active_ids", [])
        )
        return payments.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self.env.context.get("active_ids") or []
        return {
            "ids": "where pay.id in (%s)" % ", ".join(str(i) for i in ids),
            "iscopy": "%s" % self.env.context.get("iscopy", 0),
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        payments = self.env["account.payment"].browse(
            self.env.context.get("active_ids", [])
        )
        for payment in payments:
            if payment.payment_type != "inbound":
                raise ValidationError(_("Document is not Customer Receipt."))
            if payment.state not in ("posted", "reconciled"):
                raise ValidationError(
                    _("Customer Receipt(s) is not ready to Print.")
                )
        if len(payments) == 1:
            email_subject = "Customer Receipt: %s" % payments.name
            email_document_number = payments.name
            self.can_send_email = True
        else:
            email_subject = "Customer Receipt(s)"
        return super().show_report(
            report_name=report_name or "Customer Receipt(s)",
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
