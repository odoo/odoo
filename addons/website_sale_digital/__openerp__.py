# -*- encoding: utf-8 -*-
{
    'name': 'Website Sale Digital - Sell digital products',
    'version': '0.1',
    'description': """
Sell digital product using attachments to virtual products
""",
    'author': 'Odoo S.A.',
    'depends': [
        'document',
        'website_sale',
    ],
    'installable': True,
    'data': [
        'views/website_sale_digital.xml',
        'views/website_sale_digital_view.xml',
    ],
    'demo': [
        'demo.xml',
    ],
}
