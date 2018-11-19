# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Unsplash Image Library',
    'category': 'Web',
    'summary': 'Find free high-resolution images from Unsplash',
    'version': '1.1',
    'description': """Explore the free high-resolution image library of Unsplash.com and find images to use in Odoo. An Unsplash search bar is added to the image library modal.""",
    'depends': ['base_setup', 'web_editor'],
    'data': [
        'views/res_config_settings_view.xml',
        'views/web_unsplash_templates.xml',
    ],
    'auto_install': True,
}
