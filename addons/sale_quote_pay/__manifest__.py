# -*- coding: utf-8 -*-
{
    'name': "Sale Order Pay Quotation Online",
    'summary': """
        Online Singature & Payment""",
    'description': """
        Let your customers sign or pay orders online
    """,
    'website': "https://www.odoo.com/page/sale",
    'category': 'Sales',
    'version': '1.0',
    'depends': ['sale', 'mail', 'payment'],
    'data': [
        'views/sale_config_settings_views.xml',
    ],
    'demo': [],
}
