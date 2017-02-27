# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Marketing Campaign - Demo',
    'version': '1.0',
    'depends': ['marketing_campaign', 'crm'],
    'category': 'Marketing',
    'description': """
Demo data for the module marketing_campaign.
============================================

Creates demo data like leads, campaigns and segments for the module marketing_campaign.
    """,
    'website': 'https://www.odoo.com/page/lead-automation',
    'demo': ['data/marketing_campaign_crm_demo.xml'],
    'installable': True,
}
