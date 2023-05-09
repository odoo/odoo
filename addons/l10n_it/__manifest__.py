# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Italy - Accounting',
    'countries': ['it'],
    'version': '0.5',
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'author': 'OpenERP Italian Community',
    'description': """
Piano dei conti italiano di un'impresa generica.
================================================

Italian accounting chart and localization.
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/italy.html',
    'data': [
        'data/account_account_tag.xml',
        'data/account_tax_report_data.xml',
        'data/report_invoice.xml',
        'views/account_tax_views.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
