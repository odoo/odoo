# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'UTM Trackers',
    'category': 'Marketing',
    'description': """
Enable management of UTM trackers: campaign, medium, source.
""",
    'version': '1.1',
    'depends': ['base', 'web'],
    'data': [
        'data/utm_medium_data.xml',
        'data/utm_source_data.xml',
        'data/utm_stage_data.xml',
        'data/utm_tag_data.xml',
        'views/utm_campaign_views.xml',
        'views/utm_medium_views.xml',
        'views/utm_source_views.xml',
        'views/utm_stage_views.xml',
        'views/utm_tag_views.xml',
        'views/utm_menus.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/utm_campaign_demo.xml',
        'data/utm_stage_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'utm/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
