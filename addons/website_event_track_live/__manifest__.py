# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Live Event Tracks',
    'category': 'Marketing/Events',
    'sequence': 1006,
    'version': '1.0',
    'summary': 'Support live tracks: streaming, participation, youtube',
    'website': 'https://www.odoo.com/app/events',
    'depends': [
        'website_event_track',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/event_track_templates_list.xml',
        'views/event_track_templates_page.xml',
        'views/event_track_views.xml',
        'views/event_track_live_account_views.xml',
        'views/event_track_live_menus.xml',
        'views/event_track_live_post_views.xml',
        'views/res_config_settings_views.xml',
        'views/event_track_live_templates.xml',
        'wizard/event_track_post_live_wizard.xml',
    ],
    'demo': [
        'data/event_track_demo.xml'
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'website_event_track_live/static/src/js/website_event_track_live_account_list_controller.js',
            'website_event_track_live/static/src/js/website_event_track_live_account_list_view.js',
            'website_event_track_live/static/src/xml/website_event_track_live_account_templates.xml',
        ],
        'web.assets_frontend': [
            'website_event_track_live/static/src/scss/website_event_track_live.scss',
            'website_event_track_live/static/src/js/website_event_track_replay_suggestion.js',
            'website_event_track_live/static/src/js/website_event_track_suggestion.js',
            'website_event_track_live/static/src/js/website_event_track_live.js',
            'website_event_track_live/static/src/xml/website_event_track_live_templates.xml',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
