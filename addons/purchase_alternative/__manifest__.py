# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Purchase Alternative',
    'version': '0.1',
    'category': 'Supply Chain/Purchase',
    'description': """
This module allows you to manage your Purchase Alternative.
===========================================================

It helps users compare product lines across RFQs and decide to order specific products
from different vendors, enabling more flexible and cost-effective purchasing decisions.
create a call for tender by adding alternative requests for quotation to different vendors.
Make your choice by selecting the best combination of lead time, OTD and/or total amount.
By comparing product lines you can also decide to order some products from
one vendor and others from another vendor.
""",
    'depends': ['purchase'],
    'demo': ['data/purchase_alternative_demo.xml'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_views.xml',
        'wizard/purchase_alternative_warning.xml',
        'wizard/purchase_alternative_create.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_alternative/static/src/*/**.js',
            'purchase_alternative/static/src/*/**.scss',
            'purchase_alternative/static/src/*/**.xml',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
