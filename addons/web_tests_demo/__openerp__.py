{
    'name': "Demonstration of web/javascript tests",
    'category': 'Hidden',
    'description': """
OpenERP Web demo of a test suite
================================

Test suite example, same code as that used in the testing documentation.
    """,
    'depends': ['web'],
    'data' : [
        'views/web_tests_demo.xml',
    ],
    'qweb': ['static/src/xml/demo.xml'],
}
