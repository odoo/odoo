{
    'name': 'Test Tools',
    'category': 'Hidden/Tests',
    'description': """Tests the Tools.""",
    'depends': ['base'],
    'data': [
        'data/test_translated_field/test_model_data.xml',
        'security/ir.access.csv',
    ],
    'other_files': [
        'data/test_translated_field/test_tools.convert.csv',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
