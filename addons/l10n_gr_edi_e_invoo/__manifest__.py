# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Greece - myDATA E-invoicing through e-invoo',
    'countries': ['gr'],
    'category': 'Accounting/Localizations/EDI',
    'depends': ['l10n_gr_edi'],
    'data': [
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': ['l10n_gr_edi'],
    'installable': True,
    'license': 'LGPL-3',
}
