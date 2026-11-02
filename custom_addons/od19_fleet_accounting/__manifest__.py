{
    'name': 'Fleet Accounting Integration',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fleet vehicle accounting, expense tracking, and cost allocation',
    'description': """
Fleet Accounting Integration
=============================
- Vehicle expense categories (fuel, maintenance, insurance, etc.)
- Department and analytic account allocation for vehicles
- Vehicle cost analysis with expense categorization
- Integration with fleet vehicle log services
    """,
    'author': 'OD19',
    'depends': ['fleet', 'account_fleet', 'hr', 'analytic', 'od19_security_roles'],
    'data': [
        'security/ir.model.access.csv',
        'security/od19_department_rule.xml',
        'views/fleet_vehicle_views.xml',
        'views/fleet_vehicle_log_services_views.xml',
        'views/od19_vehicle_expense_category_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    "icon": "/od19_fleet_accounting/static/description/icon.svg",
}
