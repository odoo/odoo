# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

CHART_OF_ACCOUNTS = [
    ("1", "Business general accounting plan"),
    ("2", "Revised chart of accounts"),
    ("3", "Chart of accounts for companies in the financial system, supervised by SBS"),
    ("4", "Chart of accounts for healthcare providers, supervised by SBS"),
    ("5", "Chart of accounts for companies in the insurance system, supervised by SBS"),
    ("6", "Chart of accounts of private pension fund managers, supervised by SBS"),
    ("7", "Government chart of accounts"),
    ("99", "Others"),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_chart_of_accounts = fields.Selection(
        selection=CHART_OF_ACCOUNTS,
        string="Chart of Accounts PLE 5.3 (PE)",
        help="Value used on PLE 5.3 report to indicate the chart of accounts used.",
    )
