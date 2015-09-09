# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Claim on Deliveries',
    'version': '1.0',
    'category': 'Warehouse Management',
    'depends': ['crm_claim', 'stock'],
    'description': """
Create a claim from a delivery order.
=====================================

Adds a Claim link to the delivery order.
""",
    'data': [
        'data/claim_delivery_data.xml',
        'views/claim_delivery_views.xml', ],
}
