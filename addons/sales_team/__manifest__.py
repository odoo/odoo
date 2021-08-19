# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Teams',
    'version': '1.0',
    'category': 'Sales/Sales',
    'summary': 'Sales Teams',
    'description': """
Using this application you can manage Sales Teams with CRM and/or Sales
=======================================================================
 """,
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['base', 'mail'],
    'data': [
        'security/sales_team_security.xml',
        'security/ir.model.access.csv',
        'data/crm_team_data.xml',
        'views/assets.xml',
        'views/crm_tag_views.xml',
        'views/crm_team_views.xml',
        'views/mail_activity_views.xml',
        'views/res_partner_views.xml',
        ],
    'demo': [
        'data/crm_team_demo.xml',
        'data/crm_tag_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
