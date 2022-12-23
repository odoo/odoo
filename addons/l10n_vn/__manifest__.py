# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Vietnam - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['vn'],
    'version': '2.0.1',
    'author': 'General Solutions',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the module to manage the accounting chart for Vietnam in Odoo.
=========================================================================

This module applies to companies based in Vietnamese Accounting Standard (VAS)
with Chart of account under Circular No. 200/2014/TT-BTC

**Credits:**
    - General Solutions.
    - Trobz
""",
    'depends': [
        'account',
        'base_iban',
    ],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
