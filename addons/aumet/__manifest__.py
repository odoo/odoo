# -*- coding: utf-8 -*-
{
    'name': "Aumet",

    'summary': """
    Custom Module for Aumet's POS
        Includes POS Scientific names and seed command for pre-defined scientific names""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Aumet",
    'website': "http://www.aumet.com",
    'category': 'Aumet',
    'version': '0.1',

    'depends': ['product', 'base', 'base_setup', 'point_of_sale', 'purchase'],

    'data': [
        'data/aumet.scientific_name.csv',
        'views/assets.xml',
        'views/views.xml'

    ],

    'images': ['static/description/icon.png'],

    'qweb': [
        'views/templates.xml'
    ],

    'css': ["static/src/css/aumet.css"],

    'installable': True,
    'application': True,
    # 'post_init_hook': 'listener'
}
