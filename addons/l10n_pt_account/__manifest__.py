# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pt'],
    'version': '1.0',
    'author': 'Odoo',
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Portugal - Accounting',
    'depends': [
        'base',
        'account',
        'base_vat',
        'l10n_pt',
    ],
    'auto_install': [
        'account',
        'l10n_pt',
    ],
    'data': [
        'data/account_tax_report.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'views/account_tax_view.xml',
        'views/report_template.xml',
        'views/report_invoice.xml',
        'views/l10n_pt_account_menuitem.xml',
        'views/l10n_pt_account_tax_authority_series_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
