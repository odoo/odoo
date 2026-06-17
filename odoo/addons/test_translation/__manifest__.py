{
    'name': 'Test Translation',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to test translation.""",
    'depends': ['base', 'web_tour'],
    'data': [
        'view.xml',
        'data/test_translation_data.xml',
        'data/test.translation.model1.csv',
        'data/test.translation.model1-translated.csv',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'test_translation/static/tests/tours/constraint.js',
            'test_translation/static/src/xml/js_templates.xml',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
