# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hungary - E-invoicing Receive Vendor Bills',
    'category': 'Hidden',
    'description': """
Electronically receive vendor bills from the NAV (Hungarian Tax Agency).
    """,
    'depends': ['l10n_hu_edi'],
    'data': [
        'security/ir.model.access.csv',
        'data/template_requests.xml',
        'data/ir_cron.xml',
        'views/account_move_views.xml',
        'wizard/l10n_hu_edi_receive_bills_wizard_views.xml',
    ],
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'l10n_hu_edi_receive/static/src/views/**/*',
        ],
    }
}
