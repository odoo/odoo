{
    'name': 'Türkiye - e-Dispatch',
    'countries': ['tr'],
    'category': 'Accounting/Localizations/EDI',
    'description': """
Provider-independent base for the Turkish e-Dispatch (e-İrsaliye) regulated by the GİB.

The dispatches are exchanged through an integrator, which is implemented in its own module.
    """,
    'depends': ['l10n_tr_edi', 'stock_account'],
    'data': [
        'security/ir.access.csv',
        'data/edispatch_templates.xml',
        'data/ir_cron_data.xml',
        'views/account_move_views.xml',
        'views/l10n_tr_edi_vehicle_plate_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_tr_edi_stock/static/src/views/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
