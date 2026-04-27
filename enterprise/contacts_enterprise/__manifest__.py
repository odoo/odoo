# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Contacts Enterprise',
    'summary': 'Enterprise features on contacts',
    'description': 'Adds notably the map view of contact',
    'category': 'Sales/CRM',
    'version': '1.0',
    'depends': [
        'contacts',
        'web_map'
    ],
    'data': [
        "views/contact_views.xml"
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
