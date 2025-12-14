{
    'name': 'test installation of data module',
    'description': 'Test data module (see test_data_module) installation',
    'version': '0.0.1',
    'category': 'Hidden/Tests',
    'sequence': 10,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'depends': ['test_orm'],
    'data': [
        'data/ir_model.xml',
        'data/ir_model_fields.xml',
        'security/ir.model.access.csv',
    ],
}