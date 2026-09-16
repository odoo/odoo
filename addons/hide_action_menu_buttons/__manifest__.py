# -*- coding: utf-8 -*-
{
    'name': "Hide Action Menu Buttons",
    'summary': """This module helps you hide Action menu buttons based on model and group""",
    'description': """This module helps you hide Action menu buttons based on model and group""",
    'author': "Marwen Weslati",
    'website': 'https://www.linkedin.com/in/marwen-weslati/',
    'category': 'Customization',
    'depends': ['base'],

    'license': 'AGPL-3',
    'images': ['static/images/banner.png', 'static/description/icon.png'],


    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/res_config_settings.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'hide_action_menu_buttons/static/js/hide_action_buttons_list_view.js',
            'hide_action_menu_buttons/static/js/hide_action_buttons_form_view.js',
        ],
    },

    'demo': [],
    'installable': True,
    'application': True,
}
