{
    'name': 'Channel Integration Base',
    'version': '19.0.1.0.0',
    'category': 'Sales/Channel Integration',
    'summary': 'Abstract foundation for multi-channel marketplace integrations',
    'description': """
Channel Integration Base
========================
Provides the abstract foundation for connecting Odoo to external sales
channels (WooCommerce, Amazon, Walmart, etc.).

Includes:
- Abstract channel backend model (credentials, state, company scope)
- Abstract binding model (external ID ↔ Odoo record bridge)
- Sync log model (immutable audit trail for all sync operations)
- Shared security groups
    """,
    'author': 'Custom',
    'depends': ['base', 'mail'],
    'data': [
        'security/channel_security.xml',
        'security/ir.model.access.csv',
        'views/channel_sync_log_views.xml',
        'views/channel_backend_views.xml',
        'views/channel_menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
