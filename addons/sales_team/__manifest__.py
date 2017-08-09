# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sales Channels',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Sales Channels',
    'description': """
Using this application you can manage Sales Channels  with CRM and/or Sales
===========================================================================
 """,
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['base', 'mail'],
    'data': ['security/sales_team_security.xml',
             'security/ir.model.access.csv',
             'data/sales_team_data.xml',
             'views/crm_team_views.xml',
             'views/sales_team_dashboard.xml',
             ],
    'demo': ['data/sales_team_demo.xml'],
    'installable': True,
    'auto_install': False,
}
