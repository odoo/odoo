# -*- coding: utf-8 -*-
{
    'name': 'Slides',
    'version': '1.0',
    'summary': 'Share and Publish Videos, Presentations and Documents',
    'category': 'website',
    'description': """
Share and Publish Videos, Presentations and Documents'
======================================================

 * Website Application
 * Channel Management
 * Filters and Tagging
 * Statistics of Presentation
 * Channel Subscription
 * Supported document types supported: PDF, images, YouTube videos and Google Drive documents)
""",
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com',
    'depends': ['website', 'website_mail'],
    'data': [
        'view/res_config.xml',
        'view/website_slides.xml',
        'view/website_slides_embed.xml',
        'view/website_slides_backend.xml',
        'data/website_slides_data.xml',
        'security/ir.model.access.csv',
        'security/website_slides_security.xml'
    ],
    'demo': [
        'data/website_slides_demo.xml'
    ],
    'installable': True,
}
