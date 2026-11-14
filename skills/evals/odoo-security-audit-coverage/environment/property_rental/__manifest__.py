{
    'name': "Property Rental",
    'summary': "Rent properties to tenants and let them manage their leases from the portal",
    'category': 'Services/Rental',
    'version': '1.0',
    'depends': ['portal', 'mail'],
    'data': [
        'security/ir.access.csv',
        'views/rental_views.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'property_rental/static/src/js/lease_notes.js',
        ],
    },
    'author': "Odoo S.A.",
    'license': 'LGPL-3',
}
