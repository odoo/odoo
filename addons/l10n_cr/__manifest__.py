# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Costa Rica - Accounting',
    'url': 'https://github.com/CLEARCORP/odoo-costa-rica',
    'author': 'ClearCorp S.A.',
    'website': 'http://clearcorp.co.cr',
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
    'data': [
        'data/l10n_cr_res_partner_title.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
