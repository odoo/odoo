# -*- coding: utf-8 -*-
{
    'name': "Calendar Resource Views",

    'summary': """
        Adds the Resource Views Fork of FullCalendar""",

    'description': """
        Long description of module's purpose
    """,

    'author': "SYNRG Technology Solutions",
    'website': "http://www.synrgtech.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['web_calendar'],

    # always loaded
    'data': [
        'views/web_calendar.xml',
    ],
}