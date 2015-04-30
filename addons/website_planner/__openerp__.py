# -*- coding: utf-8 -*-
{
    'name': 'Website Planner',
    'summary': 'Help to configure application',
    'version': '1.0',
    'category': 'Planner',
    'description': """Plan your website strategy, design your pages, sell your products and grow your online business!""",
    'author': 'Odoo SA',
    'depends': ['planner', 'website'],
    'data': [
        'data/planner_data.xml',
        'views/website_planner.xml'
    ],
    'installable': True,
    'auto_install': True,
}
