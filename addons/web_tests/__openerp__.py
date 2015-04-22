{
    'name': 'Tests',
    'category': 'Hidden',
    'description': """
OpenERP Web test suite.
=======================

""",
    'version': '2.0',
    'depends': ['web', 'web_kanban', 'test_new_api'],
    'data' : [
        'views/web_tests.xml',
    ],
    'auto_install': True,
}
