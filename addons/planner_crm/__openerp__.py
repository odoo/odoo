# -*- coding: utf-8 -*-
{
    'name': 'CRM Planner',
    'summary': 'Help to configure application',
    'version': '1.0',
    'category': 'Planner',
    'description': """Plan your sales strategy: objectives, leads, KPIs, and much more!""",
    'author': 'Odoo SA',
    'depends': ['planner', 'crm'],
    'data': [
        'data/planner_data.xml',
        'views/planner_crm.xml'
    ],
    'installable': True,
    'auto_install': True,
}
