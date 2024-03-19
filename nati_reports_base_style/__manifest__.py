 # -*- coding: utf-8 -*-
{
    'name': "Nati Reports Base Style",

    'summary': """
        Redesign of all report, keeping the official and modern look """,

    'description': """
Many modern designs and shapes, with additional features, 
for example: line numbers, numbers in words, compatibility with different printing options,
english and arabic lable,for both LTR and RTL
    """,
    'author': "Mali, MuhlhelITS",
    'website': "http://muhlhel.com",
    'category': 'Extra Tools',
    'license': 'LGPL-3',
    'version': '1.16',
    'depends': ['base','nati_arabic_font'],
    'qweb': [],
    'data': ['views/main_inherit.xml',

    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'live_test_url': 'https://youtu.be/Ayy81m38QP8',
    'assets': {
        'web.report_assets_common': [
            'nati_reports_base_style/static/src/scss/variables.scss',
            'nati_reports_base_style/static/src/scss/invoice_style.scss',
        ],
    }

}