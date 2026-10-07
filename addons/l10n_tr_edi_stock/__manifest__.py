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
        'views/account_move_views.xml',
        'views/l10n_tr_edi_vehicle_plate_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
