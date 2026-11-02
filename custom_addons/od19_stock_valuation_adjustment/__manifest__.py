# -*- coding: utf-8 -*-
{
    'name': 'Stock Valuation Adjustment',
    'author': 'OD19',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Stock Valuation',
    'summary': 'Adjust inventory valuation with audit trail',
    'depends': ['stock', 'account'],
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/stock_valuation_adjustment_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    "icon": "/od19_stock_valuation_adjustment/static/description/icon.svg",
}
