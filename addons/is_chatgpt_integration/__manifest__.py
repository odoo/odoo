# -*- coding: utf-8 -*-
# Copyright (c) 2020-Present InTechual Solutions. (<https://intechualsolutions.com/>)

{
    'name': 'Odoo ChatGPT Integration',
    'version': '16.0.1.1.2',
    'license': 'AGPL-3',
    'summary': 'Odoo ChatGPT Integration',
    'description': 'Allows the application to leverage the capabilities of the GPT language model to generate human-like responses, providing a more natural and intuitive user experience',
    'author': 'InTechual Solutions',
    'company': 'InTechual Solutions',
    'maintainer': 'InTechual Solutions',
    'website': 'https://intechualsolutions.com',
    'depends': ['base', 'base_setup', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/chatgpt_model_data.xml',
        'data/mail_channel_data.xml',
        'data/user_partner_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'external_dependencies': {'python': ['openai']},
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
