# -*- coding: utf-8 -*-
{
    'name': "Mapsly: Smart map for Odoo",

    'summary': "Map. Geo-analysis. Multi-day Routing. Territories. Embeddable maps. Automation.",
    'description': """
        Connects your models and records to Mapsly
    """,
    'author': "Mapsly",
    'website': "https://mapsly.com/",
    'license': "OPL-1",

    'version': '16.0.0.1.0',
    'category': 'Connector',
    'depends': ['connector', 'base'],
    'data': [
        "views/data.xml"
    ],
    'images': [
        'static/description/thumbnail.png',
        'static/description/desc_img_02.png',
        'static/description/desc_img_03.png',
        'static/description/desc_img_04.jpeg',
        'static/description/desc_img_05.png',
        'static/description/desc_img_06.jpeg',
        'static/description/desc_img_07.png',
        'static/description/desc_img_08.png',
        'static/description/icon.png'
    ],
    'assets': {
        'web.assets_backend': [
            'mapsly_connector/static/src/js/mapsly_frame_view.js',
            'mapsly_connector/static/src/scss/mapsly_frame_view.scss',
        ],
    },
    'qweb': [],
    'installable': True
}
