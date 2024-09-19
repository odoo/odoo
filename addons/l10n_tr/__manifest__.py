# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Türkiye - Accounting',
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Türkiye in Odoo
==========================================================================
Türkiye accounting basic charts and localization.
-------------------------------------------------
Activates:

- Chart of Accounts

- Taxes
    """,
    'maintainer':'https://launchpad.net/~openerp-turkey, http://www.cantecim.com',
    'depends': [
        'account',
    ],
    'data': [
        # Chart of Accounts
        'data/account_chart_template_data.xml',
        "data/account.account.template-common.csv",
        "data/account.account.template-7a.csv",
        "data/account.account.template-7b.csv",
        "data/account.group.template.csv",

        # Taxes
        "data/account_tax_group_data.xml",
        "data/account_tax_template_data.xml",

        # post processing
        "data/account_chart_post_data.xml",
        "data/account_chart_template_try_loading.xml",

    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
