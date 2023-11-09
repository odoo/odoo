# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Cambodia - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['kh'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
    Chart Of Account and Taxes for Cambodia.
    """,
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'depends': [
        'account_qr_code_emv',
        'l10n_account_withholding_tax',
    ],
    'data': [
        'data/form_t7001.xml',
        'data/form_wt003.xml',
        'views/res_bank_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
