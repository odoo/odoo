{
    'name': 'Stock picking import',
    'version': '16.0.1.0.5',
    'license': 'OPL-1',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': ['stock', ],

    'data': [
        'security/ir.model.access.csv',

        'wizard/stock_picking_import_views.xml',
    ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],

}
