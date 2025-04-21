{
    'name': 'Marketing Card',
    'version': '1.1',
    'category': 'Marketing/Social Marketing',
    'summary': 'Generate dynamic shareable cards',
    'depends': ['link_tracker', 'mass_mailing', 'website'],
    'data': [
        'security/marketing_card_groups.xml',
        'security/ir.model.access.csv',
        'views/card_card_templates.xml',
        'data/card_template_data.xml',
        'views/card_card_views.xml',
        'views/card_campaign_views.xml',
        'views/card_frontend_templates.xml',
        'views/card_template_views.xml',
        'views/card_menus.xml',
        'views/mailing_mailing_views.xml',
        'views/website_templates.xml',
    ],
    'demo': [
        'demo/card_campaign_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'marketing_card/static/src/scss/*',
        ],
        'web_editor.backend_assets_wysiwyg': [
            'marketing_card/static/src/scss/mass_mailing.scss'
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
