# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Accounting/Fleet bridge',
    'category': 'Accounting/Accounting',
    'summary': 'Manage accounting with fleets',
    'depends': ['fleet', 'account'],
    'data': [
        'data/fleet_service_type_data.xml',
        'views/account_move_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/fleet_vehicle_log_services_views.xml',
        'views/account_account_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
