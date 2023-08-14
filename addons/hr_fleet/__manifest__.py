# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Fleet History',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Get history of driven cars by employees',
    'description': "",
    'depends': ['hr', 'fleet'],
    'data': [
        'views/employee_views.xml',
        'views/fleet_vehicle_views.xml',
        'wizard/hr_departure_wizard_views.xml'
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
