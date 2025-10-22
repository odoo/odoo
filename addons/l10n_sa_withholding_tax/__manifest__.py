# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi Arabia - Withholding Tax',
    'icon': '/account/static/description/l10n.png',
    'author': 'Odoo S.A.',
    'category': 'Accounting/Localizations/Account Charts',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/saudi_arabia.html',
    'description': """
Saudi Arabia Withholding Tax Module

Force the installation of the Withholding Tax on Payment module
""",
    'depends': ['l10n_account_withholding_tax', 'l10n_sa'],
    'auto_install': ['l10n_sa'],
    'license': 'LGPL-3',
}
