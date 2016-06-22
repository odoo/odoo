{
    'name': 'Report',
    'category': 'Base',
    'summary': 'Hidden',
    'version': '1.0',
    'description': """
Report
        """,
    'depends': ['base', 'web'],
    'data': [
        'views/layouts.xml',
        'views/views.xml',
        'data/report_paperformat.xml',
        'security/ir.model.access.csv',
        'views/report.xml',
        'views/ir_actions.xml',
    ],
    'qweb' : [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'auto_install': True,
}
