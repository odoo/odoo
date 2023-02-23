# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi Arabia - Accounting',
    'version': '2.0',
    'author': 'Odoo S.A., DVIT.ME',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Odoo Arabic localization for most Saudi Arabia.
""",
    'website': 'http://www.dvit.me',
    'depends': [
        'l10n_gcc_invoice',
        'account',
    ],
    'data': [
        'data/account_data.xml',
        'data/account_tax_report_data.xml',
        'views/view_move_form.xml',
        'views/report_invoice.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
