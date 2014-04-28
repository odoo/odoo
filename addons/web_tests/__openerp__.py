{
    'name': 'Tests',
    'category': 'Hidden',
    'description': """
OpenERP Web test suite.
=======================

""",
    'version': '2.0',
    'depends': ['web', 'web_kanban'],
    'js': ['static/src/js/*.js'],
    'css': ['static/src/css/*.css'],
    'auto_install': True,
}
