# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMART Marketplace Payout',
    'version': '18.0.1.0.0',
    'category': 'Sales/Marketplace',
    'summary': 'Seller payout management and commission calculation',
    'description': """
SMART Marketplace Payout Module
================================

This module handles:
- Payout batch creation and processing
- Commission calculation
- Accounting entries for payouts
- Bank transfer integration
    """,
    'depends': [
        'smart_marketplace_core',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/marketplace_payout_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

