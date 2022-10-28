# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Kenya Tremol Device EDI Integration",
    'summary': """
            Kenya Tremol Device EDI Integration
        """,
    'description': """
       This module integrates with the Kenyan G03 tremol control unit device.
    """,
    'author': 'odoo',
    'website': 'https://www.odoo.com',
    'category': 'account',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['l10n_ke'],
    'data': [
        'views/account_move_view.xml',
        'views/product_view.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_ke_edi_tremol/static/src/js/send_invoice.js',
            'l10n_ke_edi_tremol/static/src/js/get_device_info.js',
        ],
    },
}
