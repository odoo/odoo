# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Israel - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['il'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the latest basic Israelian localisation necessary to run Odoo in Israel:
================================================================================

This module consists of:
 - Generic Israel Chart of Accounts
 - Taxes and tax report
 - Multiple Fiscal positions
 """,
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_account_tag.xml',
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
