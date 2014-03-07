{
    'name': 'Report',
    'category': 'Base',
    'summary': 'Report',
    'version': '1.0',
    'description': """
Report
        """,
    'author': 'OpenERP SA',
    'depends': ['base'],
    'data': [
        'views/layouts.xml',
        'views/views.xml',
        'data/report_paperformat.xml',
        'security/ir.model.access.csv',
    ],
    'js': [
        'static/src/js/qwebactionmanager.js',
    ],
    'installable': True,
    'auto_install': True,
}
