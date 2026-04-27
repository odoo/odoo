# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_pk(self, companies):
        account_codes = [
        ]
        default_account = False
        rules_mapping = defaultdict(dict)

        # ================================================ #
        #           PK Employee Payroll Structure          #
        # ================================================ #

        self._configure_payroll_account(
            companies,
            "PK",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
