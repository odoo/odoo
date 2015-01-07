# -*- coding: utf-8 -*-
{
    'name': 'Slides',
    'version': '1.0',
    'summary': 'Publish Presentations, Videos, Documents and Infographic',
    'category': 'website',
    'description': """
Publish Presentations, Videos, Documents and Infographic Online
================================================================
You can upload presentations, videos, documents and infographic and moderate and publish and classify in different channels by category.

* Channel Management
* Filters and Tagging
* Statistic of Presentation
* Channel Subscription
* Document Type Supported (pdf, image, youtube video and google drive documents)
""",
    'author': 'Odoo S.A',
    'website': 'http://www.odoo.com',
    'depends': ['website', 'website_mail'],
    'data': [
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
