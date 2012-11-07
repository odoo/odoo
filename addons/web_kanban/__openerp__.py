{
    'name': 'Base Kanban',
    'category': 'Hidden',
    'description': """
OpenERP Web kanban view.
========================

""",
    'version': '2.0',
    'depends': ['web'],
    'js': [
        'static/src/js/kanban.js'
    ],
    'css': [
        'static/src/css/kanban.css'
    ],
    'qweb' : [
        'static/src/xml/*.xml',
    ],
    'auto_install': True
}
