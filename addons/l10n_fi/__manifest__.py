# -*- encoding: utf-8 -*-
##############################################################################
#
#    ODOO Addon module by Sprintit Ltd
#    Copyright (C) 2018 Sprintit Ltd (<http://sprintit.fi>).
#
#    Part of Odoo. See LICENSE file for full copyright and licensing details.
#
##############################################################################

{
    "name" : "Finland - Accounting",
    "version" : "12.0.0",
    "author" : "Sprintit",
    "category" : "Localization/Account Charts",
    "description": """This is the module to manage the accounting chart for Finland in Odoo.

When installed on a system without any chart of accounts, this module creates following accounting data localzied for Finland:
Chart of accounts (if COA is not defined yet), Taxes, Tax tags (used in l10n_fi_reports), Fiscal positions, Account types (used in l10n_fi_reports)
""",
    "depends" : [
        'account',
        'base_iban',
        'base_vat',
    ],
    "data" : [
        'data/account_account_tag_data.xml',
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_template_data.xml',
        'data/l10n_fi_chart_post_data.xml',
        'data/account_fiscal_position_template_data.xml',
        'data/account_chart_template_configuration_data.xml',

    ],
    "active": False,
    "installable": True,
}
