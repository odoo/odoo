{
    'name': "Türkiye - e-Irsaliye (e-Dispatch)",
    'description': "Allows the users to create the UBL 1.2.1 e-Dispatch file",
    'countries': ['tr'],
<<<<<<< b5327368234993d3829f6ea899deb20c4635be27
    'depends': ['l10n_tr_nilvera_einvoice', 'stock_account'],
||||||| dcaf4ea12ed1f41ddb1c8e1ef03a2d024b3d3436
    'depends': ['l10n_tr_nilvera', 'stock'],
=======
    'depends': ['l10n_tr_nilvera', 'stock', 'stock_account'],
>>>>>>> fb19d7be30b78f5209423350418c940f0a6c3c2d
    'license': "LGPL-3",
    'category': 'Accounting/Localizations',
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/l10n_tr_nilvera_trailer_plate_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'templates/l10n_tr_nilvera_edispatch.xml',
    ],
    'author': 'Odoo S.A.',
    'assets': {
        'web.assets_backend': [
            'l10n_tr_nilvera_edispatch/static/src/views/**/*',
        ],
    },
}
