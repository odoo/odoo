# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Claim on Deliveries',
    'version' : '1.0',
    'category' : 'Warehouse Management',
    'depends' : ['base', 'crm_claim', 'stock'],
    'demo' : [],
    'description': """
Create a claim from a delivery order.
=====================================

Adds a Claim link to the delivery order.
""",
    'data' : [
              'claim_delivery_view.xml',
              'claim_delivery_data.xml',],
    'auto_install': False,
    'installable': True,
}
