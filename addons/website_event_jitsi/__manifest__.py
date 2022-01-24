# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Event / Jitsi',
    'category': 'Marketing/Events',
    'sequence': 1002,
    'version': '1.0',
    'summary': 'Event / Jitsi',
    'website': 'https://www.odoo.com/app/events',
    'description': "",
    'depends': [
        'website_event',
        'website_jitsi',
    ],
    'demo': [],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
