# -*- coding: utf-8 -*-
{
    'name': "NEWS",
    'summary': "Latest News",
    'description': """""",
    'author': "Odoo-love",
    'website': "https://www.odoo.com/news",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'News',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web'],
    'license': 'LGPL-3',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/news.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'news/static/src/components/news_heading/news.js',
            'news/static/src/components/news_heading/news.xml',
            'news/static/src/components/news_heading/news.scss',
        ],
    },
    'installable': True,
    'application': True,
}