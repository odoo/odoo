# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Extended Addresses - Customer portal',
    'summary': 'Add extra fields on addresses for Customer Portal',
    'category': 'Sales/Sales',
    'description': """
Extended Addresses Management (Cusotmer Portal)
===============================================

This bridge module adds support for city dropdowns
in the customer portal (in specific countries).

        """,
    'data': [
        'views/portal_address_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'portal_address_extended/static/src/interactions/**/*',
        ]
    },
    'depends': ['base_address_extended', 'portal'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'auto_install': True,
}
