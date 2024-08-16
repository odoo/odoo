{
    'name': 'Marketing Card',
    'version': '1.0',
    'category': 'Marketing/Social Marketing',
    'summary': 'Generate dynamic shareable cards',
    'depends': ['link_tracker', 'website'],
    'data': [
        'security/marketing_card_groups.xml',
        'security/ir.model.access.csv',
        'views/card_card_templates.xml',
        'data/card_template_data.xml',
        'views/card_card_views.xml',
        'views/card_campaign_views.xml',
        'views/card_campaign_element_views.xml',
        'views/card_frontend_templates.xml',
        'views/card_template_views.xml',
        'views/card_menus.xml',
        'views/website_templates.xml',
        'wizards/card_card_share_views.xml',
    ],
    'demo': [
        'demo/card_campaign_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'marketing_card/static/src/card_campaign_element_field_selector/*',
            'marketing_card/static/src/scss/*',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
