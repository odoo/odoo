{
    'name': 'Estate',
    'version': '0.1',
    'depends': ['base'],
    'data': [
        # security
        'security/ir.model.access.csv',

        # views
        'views/estate_property_views.xml',
        'views/estate_property_type_views.xml',
        'views/estate_property_offer_views.xml',

        # actions used in menu must be defined first
        'views/estate_menus.xml',
    ],
    'author': 'Brian Nguyen (ngbri@odoo.com)',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
