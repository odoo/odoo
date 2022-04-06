# -*- coding: utf-8 -*-
{
    'name': "auto_index",
    'version': '0.1',
    'summary': """
Short (1 phrase/line) summary of the module's purpose, used as
subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,
    'license': 'LGPL-3',
    'category': 'Technical',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/missing_index_log_views.xml',
        'views/missing_index_views.xml',
        'views/index_statistics.xml',
    ],
}
