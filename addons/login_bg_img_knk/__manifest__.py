# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    'name': "Background image in Login page",
    'version': '16.0.1.0',
    'summary': """Module helps to set background image in Login page.| Background image | image|Login | Login page|website|""",
    'description': """Module helps to set background image in Login page.""",
    'license': 'OPL-1',
    'website': "https://www.kanakinfosystems.com",
    'author': 'Kanak Infosystems LLP.',
    'category': 'Tools',
    'depends': ['base', 'portal'],
    'data': [
        'views/res_company.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'login_bg_img_knk/static/src/css/bg_image.scss',
        ],
    },
    'images': ['static/description/banner.gif'],
    'sequence': 1,
    "application": True,
    "installable": True
}
