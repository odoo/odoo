{
    'name': 'Tests',
    'category': 'Hidden',
    'description': """
Web client test suite
=====================

""",
    'version': '2.0',
    'depends': ['web', 'web_kanban'],
    'data' : [
        'views/web_tests.xml',
    ],
    'auto_install': True,
}
