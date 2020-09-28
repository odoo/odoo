# -*- coding: utf-8 -*-
{
    'name': "Recurrency",
    'version': '1.0',
    'sequence': 30,
    'summary': 'Recurrent events',
    'description': """
        This module implements the mechanism of recurrency, this mechanism can be found
        in many modules as project, planning or calendar.
    """,
    'category': 'Productivity',
    'depends': ['base'],
    'data': [
        'security/recurrency_security.xml',
        'security/ir.model.access.csv',

    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
