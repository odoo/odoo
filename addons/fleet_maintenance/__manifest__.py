# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Maintenance - Fleet',
    'sequence': 125,
    'category': 'Human Resources',
    'description': "Bridge between Fleet and Maintenance.",
    'depends': ['fleet', 'maintenance'],
    'summary': 'Integrates Fleet and Maintenance',
    'data': [
        'security/fleet_maintenance_security.xml',
        'views/maintenance_equipment_views.xml',
        'views/fleet_vehicle_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
