# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Malaysia - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['my'],
    'author': 'Odoo PS',
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Malaysia in Odoo.
==============================================================================
    """,
    'depends': [
        'account',
        'account_tax_python',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'data/account.account.tag.csv',

        'views/product_template_view.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
