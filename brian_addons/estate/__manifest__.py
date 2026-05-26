{
    'name': 'Estate',
    'version': '0.1',
    'depends': ['base'],
    'data': [
        # security
        'security/ir.model.access.csv',
        
        # views
        'views/estate_property_views.xml',
        'views/estate_menus.xml',
    ],
    'author': 'Brian Nguyen (ngbri@odoo.com)',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}