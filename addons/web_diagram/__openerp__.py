{
    'name': 'OpenERP Web Diagram',
    'category': 'Hidden',
    'description': """
Openerp Web Diagram view.
=========================

""",
    'version': '2.0',
    'depends': ['web'],
    'data' : [
        'views/web_diagram.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True,
}
