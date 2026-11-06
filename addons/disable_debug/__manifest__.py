# -*- coding: utf-8 -*-
{
    'name': "Disable Debug Mode",

    'summary': """
        Control The use of Odoo Debug Mode By Access Group""",

    'description': """
        This module is used to disable the odoo debug mode for all users except for those
        having the Use Debug Mode group, this feature is essential is production environment.
    """,

    'author': "Taha Abujrad",
    'website': "https://github.com/taha-abujrad/disable-debug-mode",

    # for the full list
    'category': 'Production',
    'version': '0.2',
    'application': True,
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/groups.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'images': [
        'static/description/banner.png',
    ],
}
