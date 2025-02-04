# -*- coding: utf-8 -*-
{
    'name': 'test-translation-import',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to test translation import.""",
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'view.xml',
        'data/test_translation_import_data.xml',
        'data/test.translation.import.model1.csv',
        'data/test.translation.import.model1-translated.csv',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'test_translation_import/static/src/xml/js_templates.xml',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
