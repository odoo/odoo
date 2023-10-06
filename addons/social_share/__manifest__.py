# -*- coding: utf-8 -*-
{
    'name': 'Social Share',
    'version': '1.0',
    'category': 'Marketing/Social Marketing',
    'summary': 'Generate dynamic shareable cards',
    'depends': ['base_setup'],
    'data': [
        'security/social_share_security.xml',
        'security/ir.model.access.csv',
        'data/model_field_allow_list.xml',
        'views/share_post_templates.xml',
        'views/share_post_views.xml',
        'views/share_post_template_views.xml',
        'views/share_post_template_element_views.xml',
        'views/social_share_menus.xml',
        'wizards/share_url.xml'
    ],
    'demo': [
        'data/share_post_templates_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'social_share/static/src/scss/*',
        ],
        'social_share.assets_share_post': [
            'social_share/static/src/share_post/**/*',
        ],
    },
    'license': 'OEEL-1',
}
