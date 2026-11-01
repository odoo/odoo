# -*- coding: utf-8 -*-
"""R-PC-001 Petty Cash Request report.

Odoo 19 port of the legacy ``dtr_petty_cash`` report
``petty_cash_request_report``.  It lists petty cash funds together with their
transactions.

Odoo 19 adaptations applied to ``jrxml/petty_cash_request_report.jrxml``:

* ``dtr_pc_requests`` / ``dtr_pc_payment`` / ``account_analytic_account`` (and
  the analytic cost-center column) do not exist any more; the fund header is now
  read from ``petty_cash_fund`` (``pr``) and the movements from
  ``petty_cash_transaction`` (``pp``).
* ``account_account.code`` -> ``account_account.code_store`` (jsonb, keyed by the
  journal's ``company_id``) and ``account_account.name`` -> translated jsonb.
* the company header is read from the ``company_address_header_report`` view.
* opened from the Accounting > Reporting menu, so when no document is selected in
  the context the report simply lists every fund.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class PettyCashRequestReport(models.TransientModel):
    _name = "petty.cash.request.report"
    _description = "Petty Cash Request Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Petty Cash Request Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
        default="thai",
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
        ids = self.env.context.get("active_ids")
        p_Where = (
            "WHERE pr.id in ({0})".format(
                ", ".join(str(i) for i in ids)
            )
            if ids
            else ""
        )

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_Where": p_Where,
            }
        )
        return parameters
