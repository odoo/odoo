# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Configure a Twitter Wall on your Event',
    'category': 'Marketing/Events',
    'sequence': 1030,
    'version': '1.1',
    'summary': 'Bridge module to configure a twitter wall on your event',
    'website': 'https://www.odoo.com/app/events',
    'depends': [
        'website_twitter_wall',
        'website_event',
    ],
    'data': [
        'views/event_event_views.xml',
        'views/event_twitter_wall_templates.xml',
        'views/event_type_views.xml',
    ],
    'demo': [
        'data/event_twitter_wall_demo.xml'
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_event_twitter_wall/static/**/*',
        ],
    },
    'license': 'OEEL-1',
}
