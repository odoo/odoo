# -*- coding: utf-8 -*-
{
    'name': "scheduler_notif_todo",

    'summary': """This module will send daily work need to be done that automatically runs daily.""",

    'description': """
        This module will send daily work need to be done that automatically runs daily.
        """,

    'author': "E+Craftman Vietnam Co., Ltd.",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [

	'data/scheduler_data.xml',

        # 'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
