# -*- coding: utf-8 -*-
{
    'name': 'OD19 Stock FIFO Valuation',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': (
        'FIFO stock valuation service, monthly stock report email, '
        'FIFO as-of wizard, and BF (ยกมา) revaluation.'
    ),
    'author': 'OD19',
    'website': 'https://od19.com',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'stock_account',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/mail_template.xml',
        'views/stock_fifo_views.xml',
        'wizards/stock_fifo_asof_views.xml',
        'wizards/stock_bf_revaluation_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    "icon": "/od19_stock_fifo/static/description/icon.svg",
}
