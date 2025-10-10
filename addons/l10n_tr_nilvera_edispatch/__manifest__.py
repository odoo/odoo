{
    'name': "Türkiye - e-Irsaliye (e-Dispatch)",
    'description': "Allows the users to create the UBL 1.2.1 e-Dispatch file",
    'countries': ['tr'],
    'version': "1.0",
    'depends': ['l10n_tr_nilvera', 'stock'],
    'installable': True,
    'license': "LGPL-3",
    'category': 'Accounting/Localizations',
    'data': [
        'security/ir.model.access.csv',
        'views/l10n_tr_nilvera_trailer_plate_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'templates/l10n_tr_nilvera_edispatch.xml'
    ],
}
