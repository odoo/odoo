# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indonesian - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['id'],
    'version': '1.3',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the latest Indonesian Odoo localisation necessary to run Odoo accounting for SMEs with:
=================================================================================================
    - generic Indonesian chart of accounts
    - tax structure""",
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/indonesia.html',
    'depends': [
        'account',
        'base_vat',
        'l10n_account_withholding_tax',
    ],
    'auto_install': ['account'],
    'data': [
        'security/ir.access.csv',
        'data/ir_cron.xml',
        'data/l10n_id.ebupot.code.csv',
        'views/account_tax_views.xml',
        'views/account_move_views.xml',
        'views/res_bank.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'post_init',
    'license': 'LGPL-3',
}
