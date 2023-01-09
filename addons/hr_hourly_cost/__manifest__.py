# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Hourly Wage',
    'version': '1.0',
    'category': 'Services/Employee Hourly Cost',
    'summary': 'Employee Hourly Wage',
    'description': """
This module assigns an hourly wage to employees to be used by other modules.
============================================================================

    """,
    'depends': ['hr'],
    'data': [
        'views/hr_employee_views.xml',
    ],
    'demo': [
        'data/hr_hourly_cost_demo.xml',
    ],
    'license': 'LGPL-3',
}
