# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Myanmar - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mm'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
    Chart Of Account and Taxes for Myanmar.
    """,
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'depends': [
        'account_qr_code_emv',
        'l10n_account_withholding_tax',
    ],
    'data': [
        'views/res_bank_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
