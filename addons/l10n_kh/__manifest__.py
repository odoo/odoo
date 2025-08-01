# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Cambodia - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['kh'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'license': 'LGPL-3',
    'description': """Added Khmer Chart of Account, Taxes and KHQR Support.""",
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'depends': [
        'account',
        'account_qr_code_emv',
    ],
    'data': [
        "views/res_company_views.xml",
        "views/res_bank_views.xml"
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}
