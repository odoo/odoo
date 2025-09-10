# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Italy - Accounting',
    'countries': ['it'],
    'version': '0.8',
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'auto_install': ['account'],
    'author': 'OpenERP Italian Community',
    'description': """
Piano dei conti italiano di un'impresa generica.
================================================

Italian accounting chart and localization.
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/italy.html',
    'data': [
        'data/account_account_tag.xml',
        'data/tax_report/account_monthly_tax_report_data.xml',
        'data/tax_report/annual_report_sections/va.xml',
        'data/tax_report/annual_report_sections/ve.xml',
        'data/tax_report/annual_report_sections/vf.xml',
        'data/tax_report/annual_report_sections/vh.xml',
        'data/tax_report/annual_report_sections/vj.xml',
        'data/tax_report/annual_report_sections/vl.xml',
        'data/tax_report/account_annual_tax_report_data.xml',
        'data/account_tax_report_data.xml',
        'views/account_tax_views.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
