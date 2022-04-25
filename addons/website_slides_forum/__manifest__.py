# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Forum on Courses',
    'category': 'Website/eLearning',
    'version': '1.0',
    'summary': 'Allows to link forum on a course',
    'description': """A Slide channel can be linked to forum. Also, profiles from slide and forum are regrouped together""",
    'depends': [
        'website_slides',
        'website_forum'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/website_slides_forum_security.xml',
        'views/forum_views.xml',
        'views/res_config_settings_views.xml',
        'views/slide_channel_views.xml',
        'views/website_slides_menu_views.xml',
        'views/website_slides_forum_templates.xml',
        'views/website_slides_templates.xml',
    ],
    'demo': [
        'data/slide_channel_demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
