# -*- coding: utf-8 -*-

{
    'name': 'Web Studio Tests',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9876,
    'summary': 'Web studio Test',
    'description': """This module contains tests related to web studio. Those are
present in a separate module as it contains models used only to perform
tests independently to functional aspects of other models. """,
    'depends': ['web_studio', 'website'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'license': 'OEEL-1',
    "assets": {
        'web.assets_tests': [
            'test_web_studio/static/tests/**/*',
        ],
    }
}
