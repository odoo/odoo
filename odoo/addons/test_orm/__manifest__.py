{
    'name': 'Test ORM',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """A module to test the ORM.""",
    'depends': ['base', 'web', 'web_tour'],
    'installable': True,
    'data': [
        'security/ir.model.access.csv',
        'security/test_orm_security.xml',
        'views/test_orm_views.xml',
        'data/test_orm_data.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'test_orm/static/tests/tours/constraint.js',
            'test_orm/static/tests/tours/x2many.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
