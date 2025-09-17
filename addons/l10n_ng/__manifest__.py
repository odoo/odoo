# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Nigeria - Accounting",
    'description': """
Nigerian localization.
=========================================================
    """,
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'version': '1.0',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ng'],
    'category': 'Accounting/Localizations/Account Charts',
    'depends': ['base_vat', 'account'],
    'data': [
        'data/tax_report.xml',
        'data/withholding_vat_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
