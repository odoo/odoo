# -*- coding: utf-8 -*-
{
    'name': "OpenAcademy",

    'summary': """
        Course management""",

    'description': """
        Open Academy allow you to manager you course, session, teacher and attendee. 
    """,

    'author': "Odoo",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/10.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Academy',
    'version': '0.1',

    # EX01 : add mail in dependencies
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/partner.xml',
        'views/courses.xml',
        'views/sessions.xml',
        'views/partners.xml',
        'views/attendee.xml',
        'wizard/add_attendee_view.xml',
        'data/partner.xml',
        'data/email_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}