# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Quotation Builder',
    'category': 'Sales/Sales',
    'summary': 'Build great quotation templates',
    'website': 'https://www.odoo.com/page/quote-builder',
    'version': '1.0',
    'description': "Design great quotation templates with building blocks to significantly boost your success rate.",
    'depends': ['website', 'sale_management', 'website_mail'],
    'data': [
        'data/sale_order_template_data.xml',
        'views/sale_portal_templates.xml',
        'views/sale_order_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
}
