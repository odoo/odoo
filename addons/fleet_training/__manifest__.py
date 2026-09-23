# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Fleet Training",
    'version': '20.0.1.0.0',
    'category': 'Fleet Training',
    'summary': "Manage a company vehicle fleet: vehicles, drivers, assignments and maintenance",
    'description': """
Fleet Training
==============
A teaching module built chapter by chapter to demonstrate the Odoo
Server Framework concepts (models, security, views, relations,
computed fields, constraints, inheritance, reports, wizards, ...)
on top of a realistic Fleet Management use case.
""",
    'author': "Odoo Training",
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/fleet_training_groups.xml',
        'security/ir.access.csv',
        'wizard/fleet_maintenance_wizard_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/fleet_vehicle_menus.xml',
        'views/fleet_driver_views.xml',
        'views/fleet_category_views.xml',
        'views/fleet_maintenance_views.xml',
        'views/res_partner_views.xml',
        'reports/fleet_vehicle_report.xml',
        'views/fleet_vehicle_analysis_views.xml',
        'data/ir_cron_data.xml',
    ],
    'demo': [
        'demo/fleet_training_demo.xml',
    ],
    'application': True,
}
