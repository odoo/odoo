# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Thailand - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['th'],
    'version': '2.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Chart of Accounts for Thailand.
===============================

Thai accounting chart and localization.
    """,
    'author': 'Almacom (http://almacom.co.th/)',
<<<<<<< HEAD
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/thailand.html',
||||||| parent of d9e3022e72f (temp)
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
=======
    'website': 'https://www.odoo.com/documentation/saas-16.4/applications/finance/fiscal_localizations.html',
>>>>>>> d9e3022e72f (temp)
    'depends': [
        'account_qr_code_emv',
    ],
    'data': [
        'data/account_tax_report_data.xml',
        'views/report_invoice.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': '_preserve_tag_on_taxes',
    'license': 'LGPL-3',
}
