# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Twitter Snippet',
    'category': 'Website/Website',
    'summary': 'Twitter scroller snippet in website',
    'version': '1.0',
    'description': """
This module adds a Twitter scroller building block to the website builder, so that you can display Twitter feeds on any page of your website.
    """,
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'data/website_twitter_data.xml',
        'views/res_config_settings_views.xml',
        'views/website_twitter_snippet_templates.xml'
    ],
    'installable': True,
}
