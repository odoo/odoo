# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Payment: Website Integration',
    'category': 'Website',
    'summary': 'Payment: Website Integration',
    'version': '1.0',
    'description': """Bridge module for acquirers and website.""",
    'author': 'Odoo SA',
    'depends': [
        'website',
        'payment',
        'website_portal',
    ],
    'data': [
        'views/website_payment_templates.xml',
        'views/website_views.xml',
    ],
}
