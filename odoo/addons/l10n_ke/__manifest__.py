# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Kenya - Accounting',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/kenya.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ke'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This provides a base chart of accounts and taxes template for use in Odoo.
    """,
    'depends': [
        'account',
    ],
    'data': [
        'views/account_tax_views.xml',
        'views/l10n_ke_item_code_views.xml',
        'data/l10n_ke.item.code.csv',
        'data/account_tax_report_data.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
