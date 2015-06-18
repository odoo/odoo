# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Sale Digital - Sell digital products',
    'description': """
Sell digital product using attachments to virtual products
""",
    'depends': [
        'document',
        'website_sale',
    ],
    'data': [
        'views/product_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/product_template_demo.xml',
        'data/ir_attachment_demo.xml'
    ],
}
