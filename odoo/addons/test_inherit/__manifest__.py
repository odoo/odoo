{
    'name': 'test-inherit',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to verify the inheritance.""",
    'depends': ['base', 'test_orm'],
    'data': [
        'data/demo_data.xml',
        'security/ir.access.csv',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'is_test_module': True,
}
