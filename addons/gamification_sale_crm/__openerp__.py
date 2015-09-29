# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'CRM Gamification',
    'version': '1.0',
    'category': 'hidden',
    'depends': ['gamification','sale_crm'],
    'website' : 'https://www.odoo.com/page/gamification',
    'description': """Example of goal definitions and challenges that can be used related to the usage of the CRM Sale module.""",
    'data': ['sale_crm_goals.xml'],
    'demo': ['sale_crm_goals_demo.xml'],
    'auto_install': True,
}
