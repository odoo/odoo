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
        'views/layout_templates.xml',
        'views/report_paperformat_views.xml',
        'data/report_paperformat_data.xml',
        'security/ir.model.access.csv',
        'views/report_templates.xml',
        'views/res_company_views.xml',
        'views/ir_actions_report_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
