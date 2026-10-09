# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Greece - myDATA E-invoicing through e-invoo (direct API)',
    'author': 'Odoo',
    'countries': ['gr'],
    'category': 'Accounting/Localizations/EDI',
    'depends': ['l10n_gr_edi', 'l10n_gr_edi_e_invoo'],
    'data': [
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
}
