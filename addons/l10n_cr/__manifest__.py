# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Costa Rica - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['cr'],
    'url': 'https://github.com/CLEARCORP/odoo-costa-rica',
    'author': 'ClearCorp S.A.',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Chart of accounts for Costa Rica.
=================================

Includes:
---------
    * account.account.template
    * account.tax.template
    * account.chart.template

Everything is in English with Spanish translation. Further translations are welcome,
please go to http://translations.launchpad.net/openerp-costa-rica.
    """,
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/l10n_cr_res_partner_title.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
