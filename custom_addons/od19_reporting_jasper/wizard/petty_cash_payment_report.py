# -*- coding: utf-8 -*-
"""R-PC-002 Petty Cash Payment report.

Odoo 19 port of the legacy ``dtr_petty_cash`` report
``petty_cash_payment_report``.  It lists petty cash transactions for a period,
grouped by their expense account.

Odoo 19 adaptations applied to ``jrxml/petty_cash_payment_report.jrxml``:

* ``dtr_pc_payment`` does not exist any more; the movements are now
  ``petty_cash_transaction`` (``pc``).  The legacy ``ref`` column has no
  equivalent, so the transaction ``note`` is printed in its place.
* ``account_account.code`` -> ``account_account.code_store`` (jsonb, keyed by the
  journal's ``company_id``) and ``account_account.name`` -> translated jsonb.
* the company header is read from the ``company_address_header_report`` view.
* the legacy statuses ``wait_approve`` / ``open`` / ``done`` collapsed into the
  Odoo 19 ``petty.cash.transaction.state`` selection (``draft`` / ``posted``).
"""
from datetime import date

from odoo import fields, models

from .invoice_form import DATE_FORMATS


class PettyCashPaymentReport(models.TransientModel):
    _name = "petty.cash.payment.report"
    _description = "Petty Cash Payment Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Petty Cash Payment Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
        default="thai",
    )
    p_Start_Date = fields.Date(
        string="Start Date", required=True, default=lambda self: self._default_start_date()
    )
    p_End_Date = fields.Date(
        string="End Date", required=True, default=fields.Date.context_today
    )
    p_fund_id = fields.Many2one(
        "petty.cash.fund",
        string="Fund",
        default=lambda self: self.env["petty.cash.fund"]
        .search([("state", "=", "active")], limit=1),
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

    def _default_start_date(self):
        today = fields.Date.context_today(self)
        return date(today.year, today.month, 1)

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        p_Where = (
            "WHERE pc.state in ('draft', 'posted') "
            "AND date(pc.date) >= '{0}' AND date(pc.date) <= '{1}'"
        ).format(self.p_Start_Date, self.p_End_Date)
        if self.p_fund_id:
            p_Where += " AND pc.fund_id = {0}".format(self.p_fund_id.id)

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_Where": p_Where,
                "p_Start_Date": str(self.p_Start_Date),
                "p_End_Date": str(self.p_End_Date),
                "p_fund": self.p_fund_id.name or "",
            }
        )
        return parameters
