{
    'name': 'Sales Margins in Projects',
    'summary': 'Bridge module between Sales Margin and Project',
    'description': """
Allows to compute accurate margin for Service sales.
======================================================
""",
    'category': 'Sales/Sales',
    'depends': ['sale_margin', 'sale_project', 'spreadsheet_dashboard'],
    'auto_install': True,
    'data': [
        'views/project_task_views.xml',
        'views/project_menus.xml',
        'report/sale_report_views.xml',
        'data/dashboards.xml',
        'security/ir.access.csv',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
