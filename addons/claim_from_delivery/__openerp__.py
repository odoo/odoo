# -*- coding: utf-8 -*-
{
    'name' : 'Claim on Deliveries',
    'version' : '1.0',
    'author' : 'Odoo SA',
    'category' : 'Warehouse Management',
    'depends' : ['base', 'crm_claim', 'stock'],
    'demo' : [],
    'description': """
Create a claim from a delivery order.
=====================================

Adds a Claim link to the delivery order.
""",
    'data' : ['views/claim_delivery_view.xml',
              'data/claim_delivery_data.xml'],
    'installable': True,
}
