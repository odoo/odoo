{
    'name': 'Fleet Insurance & Service Notifications',
    'version': '19.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Insurance/Act expiry and service done notifications for fleet vehicles',
    'description': """
Fleet Insurance & Service Notifications
=======================================
- Insurance and Act (tax) expiry date fields on fleet vehicles
- Configurable reminder days before expiry
- Weekly cron that emails fleet managers about upcoming/expired insurance and Act
- Notification when a vehicle service log is marked as done
- Optional integration with od19_notification_multi_channel when available
    """,
    'author': 'OD19',
    'license': 'LGPL-3',
    'depends': [
        'fleet',
        'mail',
    ],
    'data': [
        'data/mail_template.xml',
        'data/ir_cron.xml',
        'views/fleet_vehicle_views.xml',
    ],
    'installable': True,
    'application': False,
    "icon": "/od19_fleet_notification/static/description/icon.svg",
}
