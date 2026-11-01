# -*- coding: utf-8 -*-
"""R-CT-001 Cheque Paid Balance report.

Odoo 19 port of the legacy ``dtr_cheque`` report ``cheque_balance_report``.
It lists confirmed cheques grouped by the bank account of the cheque journal.

Odoo 19 adaptations applied to ``jrxml/cheque_balance_report.jrxml``:

* the legacy ``dtr_cheque`` / ``dtr_cheque_leaf`` pair was replaced by the
  single ``account_cheque`` model (``od19_accounting_cheque``), so the two-branch
  UNION collapsed into one query.  The legacy ``cheque_status = 'wait'``
  (Wait Confirm) maps to the Odoo 19 ``account_cheque.state = 'confirmed'``.
* ``account_journal.default_credit_account_id`` / ``default_debit_account_id``
  were removed in Odoo 17+; the bank account is now
  ``account_journal.default_account_id``.
* ``account_account.code`` is stored per company in ``account_account.code_store``
  (jsonb, keyed by ``company_id``) and ``account_account.name`` is a translated
  jsonb column.
* the company header is read from the ``company_address_header_report`` view.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class ChequeBalanceReport(models.TransientModel):
    _name = "cheque.balance.report"
    _description = "Cheque Balance Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Cheque Paid Balance Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
        default="thai",
    )
    p_account_no_from_id = fields.Many2one(
        "account.account", string="Account No. (From)"
    )
    p_account_no_to_id = fields.Many2one(
        "account.account", string="Account No. (To)"
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

    def _account_number(self, account):
        """Digits-only account code used by the legacy range comparison."""
        code = (account.code or "").replace("-", "")
        return int(code) if code.isdigit() else None

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        p_Where = "WHERE a.cheque_status = 'confirmed'"
        p_account_display = ""
        account_ids = self.env["account.account"]
        if self.p_account_no_from_id or self.p_account_no_to_id:
            display = []
            if self.p_account_no_from_id:
                display.append(self.p_account_no_from_id.display_name)
            if self.p_account_no_to_id:
                display.append(self.p_account_no_to_id.display_name)
            p_account_display = " - ".join(display)

            start = self.p_account_no_from_id and self._account_number(
                self.p_account_no_from_id
            )
            end = self.p_account_no_to_id and self._account_number(
                self.p_account_no_to_id
            )
            for account in self.env["account.account"].search([]):
                number = self._account_number(account)
                if number is None:
                    continue
                if start is not None and number < start:
                    continue
                if end is not None and number > end:
                    continue
                account_ids |= account
        else:
            p_account_display = "All" if self.p_language == "english" else "ทั้งหมด"

        if account_ids:
            p_Where += " AND a.account_id in ({0})".format(
                ", ".join(str(account.id) for account in account_ids)
            )

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_Where": p_Where,
                "p_account_display": p_account_display,
            }
        )
        return parameters
