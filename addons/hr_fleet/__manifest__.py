# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Fleet History',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Get history of driven cars by employees',
    'depends': ['hr', 'fleet'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_fleet_security.xml',
        'views/employee_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/fleet_vehicle_cost_views.xml',
        'wizard/hr_departure_wizard_views.xml',
    ],
    'demo': [
        'data/hr_fleet_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_fleet/static/src/views/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
