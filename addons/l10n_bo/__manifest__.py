# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bolivia - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['bo'],
    'version': '2.0',
    'description': """
Bolivian accounting chart and tax localization.

Plan contable boliviano e impuestos de acuerdo a disposiciones vigentes

    """,
    'author': 'Odoo / Kyohei Ltda',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'account_tax_python'
    ],
    'auto_install': ['account'],
    'data': [
        'data/tax_reports/form_200_v5_tax_report_data.xml',
        'data/tax_reports/form_400_v5_tax_report_data.xml',
        'data/tax_reports/form_410_v2_tax_report_data.xml',
        'data/tax_reports/form_500_v2_tax_report_data.xml',
        'data/tax_reports/form_530_v3_tax_report_data.xml',
        'data/tax_reports/form_550_v3_tax_report_data.xml',
        'data/tax_reports/form_551_v3_tax_report_data.xml',
        'data/tax_reports/form_570_v2_tax_report_data.xml',
        'data/tax_reports/form_604_v3_tax_report_data.xml',
        'data/country_data.xml',
        'data/state_data.xml',
        'data/contact_bank_data.xml',
        'data/language_data.xml',
    ],
    'license': 'LGPL-3',
}
