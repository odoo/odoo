# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'YouTube Live Event Tracks with Thumbnail',
    'category': 'Marketing/Events',
    'sequence': 1009,
    'version': '1.0',
    'website': 'https://www.odoo.com/app/events',
    'depends': ['website_event_track_live', 'marketing_card'],
    'data': [
        'data/card_dimension_data.xml',
        'data/card_template_data.xml',
        'views/card_card_templates.xml',
        'wizard/event_track_post_live_wizard.xml',
    ],
    'demo': [
        'demo/card_campaign_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
