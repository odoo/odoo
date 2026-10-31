{
    'name': 'Populate',
    'version': '0.1',
    'summary': 'Generate synthetic data for an Odoo database',
    'description': 'Generate synthetic data for an Odoo database, following a predefined blueprint. Used for performance testing.',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'category': 'Hidden/Tools',
    'depends': ['base'],
    'external_dependencies': [
        {'pypi': 'faker', 'apt': 'faker', 'optional': True},
    ],
    'data': [
        'security/ir.access.csv',
    ],
}
