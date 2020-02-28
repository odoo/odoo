# -*- coding: utf-8 -*-
{
    'name': "sale_project_mrp",
    'summary': """Task generation from Kit in Sales Orders""",
    'description': """
        Allow to create a task/project from your sales orders if a service is part of a kit according to the settings of the service.
    """,
    'category': 'Hidden',
    'version': '0.1',
    'depends': ['base', 'sale_mrp', 'sale_project'],
    'auto_install': True,
    'data': [
        'views/assets.xml',
    ],
}
