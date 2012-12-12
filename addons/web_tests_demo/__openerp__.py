{
    'name': "Demonstration of web/javascript tests",
    'category': 'Hidden',
    'description': """ 
        OpenERP Web test demo suite.
        =======================
    """,
    'depends': ['web'],
    'js': ['static/src/js/demo.js'],
    'test': ['static/test/demo.js'],
    'qweb': ['static/src/xml/demo.xml'],
}
