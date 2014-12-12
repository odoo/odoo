# -*- coding: utf-8 -*-
{
    'name': "crm_voip",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "OpenERP SA",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','crm','mail','email_template'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/crm_voip.xml',
        'views/phonecall.xml',
        'views/opportunities.xml',
        'views/crm_voip_tip.xml',
        'views/res_config_view.xml',
        'views/res_users_view.xml',
        'templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
    'js': ['static/src/js/*.js'],
    'css': ['static/src/css/*.css'],
    'qweb': ['static/src/xml/*.xml'],
    'application' : True,
}