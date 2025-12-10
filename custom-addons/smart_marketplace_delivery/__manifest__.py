# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMART Marketplace Delivery (Sha6er)',
    'version': '18.0.1.0.0',
    'category': 'Sales/Marketplace',
    'summary': 'Sha6er delivery integration for marketplace',
    'description': """
SMART Marketplace Delivery Module
=================================

This module integrates with Sha6er delivery service:
- Create shipments via Sha6er API
- Track delivery status
- OTP verification and delivery proofs
- Webhook handling for status updates
    """,
    'depends': [
        'smart_marketplace_core',
        'delivery',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/marketplace_delivery_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

