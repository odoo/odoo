# -*- coding: utf-8 -*-
{
    'name': 'Project Planner',
    'summary': 'Help to configure application',
    'version': '1.0',
    'category': 'Planner',
    'description': """Plan your project, tasks and much more!""",
    'author': 'Odoo SA',
    'depends': ['planner', 'project'],
    'data': [
        'data/planner_data.xml',
        'views/planner_project.xml'
    ],
    'installable': True,
    'auto_install': True,
}
