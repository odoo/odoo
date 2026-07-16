{
    'name': 'Training Module',
    'version': '1.0',
    'category': 'Training',
    'summary': 'Custom module for Odoo training exercises',
    'depends': ['base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
