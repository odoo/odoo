# -*- coding: utf-8 -*-
{
    'name': "pinyin search,拼音简码搜索产品、合作伙伴",

    'summary': """
        pinyin search,拼音简码搜索-产品、合作伙伴""",

    'description': """
        pinyin search,拼音简码搜索-产品、合作伙伴
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "http://47.104.249.25",

    'category': 'tools',
    'version': '13.0',
    'license': 'OPL-1',

    'depends': ['base', 'product'],

    'data': [
        'views/product.xml',
        'views/partner.xml',
    ],

    'images': [
        'static/description/theme.jpg',
    ],
    'application':True,
    'installable': True,
    'active': True,
    'price': 5,
    'currency': 'EUR',
    'auto_install': False,
}
