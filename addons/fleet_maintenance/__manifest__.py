# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Maintenance - Fleet',
    'version': '1.0',
    'sequence': 125,
    'category': 'Human Resources',
    'description': "Bridge between Fleet and Maintenance.",
    'depends': ['fleet', 'maintenance'],
    'summary': 'Integrates Fleet and Maintenance for unified equipment and asset management.',
    'data': [
        'views/maintenance_equipment_views.xml',
        'views/fleet_vehicle_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
