# -*- coding: utf-8 -*-
{
    'name': 'Website Service (IAP)',
    'category': 'Tools',
    'version': '1.0',
    'description': """Provide and generate custom resources (images, themes, texts,...) based on website survey data.""",
    'data': [
        'security/ir.model.access.csv',
        'data/website.industry.csv',
        'data/website.industry.theme.link.csv',
        'data/website.industry.image.csv',
        'views/website_service_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
