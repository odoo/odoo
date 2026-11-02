# -*- coding: utf-8 -*-
{
    'name': 'Service Warranty & Claims',
    'author': 'OD19',
    'version': '19.0.1.0.0',
    'category': 'Services/After-Sales',
    'summary': 'Warranty management and RMA/claims on top of repair',
    'depends': ['repair', 'product_expiry', 'stock'],
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/stock_lot_views.xml',
        'views/warranty_claim_views.xml',
        'views/repair_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    "icon": "/od19_service_warranty/static/description/icon.svg",
}
