# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sales Teams',
    'version': '1.0',
    'author': 'OpenERP SA',
    'category': 'Sales Management',
    'summary': 'Sales Team',
    'description': """
Using this application you can manage Sales Team  with CRM and/or Sales 
=======================================================================
 """,
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['base','mail'],
    'data': [
        'security/ir.model.access.csv',
        'sales_team_data.xml',
        'sales_team.xml',
        'sales_team_dashboard.xml',
    ],
    'demo': ['sales_team_demo.xml'],
    'css': ['static/src/css/sales_team.css'],
    'installable': True,
    'auto_install': True,
}
