# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Opportunity to Quotation',
    'version': '1.0',
    'category': 'Hidden',
    'description': "Bridge module between sale_crm and sale_management",
    'depends': ['sale_management', 'sale_crm'],
    'data': [
        'views/partner_views.xml',
        'views/sale_order_views.xml',
        'views/crm_lead_views.xml',
        'views/crm_team_views.xml',
    ],
    'auto_install': True,
    'uninstall_hook': 'uninstall_hook'
}
