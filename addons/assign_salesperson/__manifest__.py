# -*- coding: utf-8 -*-
# Part of TechUltra Solutions. See LICENSE file for full copyright and licensing details.
{
    'name': "Assign Salesperson",
    'version': '16.0.1',
    'category': 'CRM',
    'summary': """
        Module To Assign Salesperson to multiple leads from wizard.
        """,
    'description': """
       CRM Lead
       Crm
       Lead
       Assign
       Salesperson
       Salesperson Assign
       Assign Salesperson
    """,
    'author': "TechUltra Solutions Private Limited",
    'company': 'TechUltra Solutions Private Limited',
    'website': "https://www.techultrasolutions.com/",
    'depends': ['crm'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/assign_salesperson_wizard.xml',
    ],
    'images': [
        'static/description/banner.jpg',
        'static/description/main_screen.gif'
    ],

    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
