# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Opportunity to Quotation',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
Generate quotations from opportunities
======================================

This module adds a button on opportunities on the basis of which you can generate a quotation.
The opportunity is then closed and linked to the generated sales order.
When several opportunities are selected, a separate quotation is generated for each of them.
""",
    'depends': ['sale', 'crm'],
    'data': [
        'views/sale_order_views.xml',
        'views/crm_lead_views.xml',
        'wizard/crm_opportunity_to_quotation_views.xml'
    ],
    'auto_install': True,
}
