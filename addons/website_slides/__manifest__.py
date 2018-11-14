# -*- coding: utf-8 -*-
{
    'name': 'Slides',
    'version': '1.0',
    'sequence': 145,
    'summary': 'Publish videos, slides and documents',
    'website': 'https://www.odoo.com/page/slides',
    'category': 'Website',
    'description': """
Share and Publish Videos, Presentations and Documents'
======================================================

 * Website Application
 * Channel Management
 * Filters and Tagging
 * Statistics of Presentation
 * Channel Subscription
 * Supported document types : PDF, images, YouTube videos and Google Drive documents)
""",
    'depends': ['website', 'website_mail'],
    'data': [
        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/website_slides_templates.xml',
        'views/website_slides_embed_templates.xml',
        'views/slide_slide_views.xml',
        'views/slide_channel_views.xml',
        'views/website_slides_menu_views.xml',
        'data/website_slides_ir_data.xml',
        'data/mail_data.xml',
        'data/slide_data.xml',
        'data/website_data.xml',
        'security/ir.model.access.csv',
        'security/website_slides_security.xml'
    ],
    'demo': [
        'data/website_slides_demo.xml'
    ],
    'installable': True,
    'application': True,
}
