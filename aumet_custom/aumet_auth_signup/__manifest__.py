# -*- coding: utf-8 -*-
{
    'name': "aumet_auth_signup",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,
    'images': ['static/description/icon.png'],

    'author': "Aumet",
    'website': "http://www.aumet.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Theme',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup', 'auth_signup', 'mail'],

    # always loaded
    'data': [
        'data/aumet_auth_signup_data.xml',
        'views/webclient_templates.xml',
        'views/website_templates.xml',
    ],

}
