# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Kenya Tremol Device EDI Integration",
    'countries': ['ke'],
    'summary': "Kenya Tremol Device EDI Integration",
    'description': """
This module integrates with the Kenyan G03 Tremol control unit device to the KRA through TIMS.
    """,
    'author': 'Odoo',
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['l10n_ke'],
    'data': [
        'views/account_move_view.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_view.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_ke_edi_tremol/static/src/components/*',
        ],
    },
}
