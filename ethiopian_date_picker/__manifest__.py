{
    'name': 'ET Date Picker',
    'version': '1.0',
    'category': 'Localization',
    'summary': 'Ethiopian Calendar Integration for Odoo',
    'author':'Yihune Zewdie',
    'description': """
        This module adds Ethiopian calendar support to Odoo.
        It provides date conversion between Gregorian and Ethiopian calendars
        for both purchase and sale modules.
    """,
    'depends': ['web', 'sale', "purchase"],
    'external_dependencies':{
        'python':['ethiopian_date']
    },
    'data': [
       'views/sale_order.xml',
       'views/purchase_order.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ethiopian_date_picker/static/src/js/ethiopian_date.js',
            'ethiopian_date_picker/static/src/js/et_date_picker.js',
            'ethiopian_date_picker/static/src/xml/et_date_picker.xml',
            'ethiopian_date_picker/static/src/css/ethiopian_calendar.css',
        ],

    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}