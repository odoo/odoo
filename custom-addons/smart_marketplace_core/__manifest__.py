# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMART Marketplace Core',
    'version': '18.0.1.0.0',
    'category': 'Sales/Marketplace',
    'summary': 'Multi-vendor marketplace core functionality',
    'description': """
SMART Marketplace Core Module
==============================

This module provides the core functionality for a multi-vendor marketplace:
- Seller management with KYC workflow
- Product extensions for marketplace
- Commission engine
- Seller portal
- Multi-seller order management
    """,
    'depends': [
        'base',
        'website_sale',
        'sale_management',
        'stock',
        'account',
        'portal',
        'mail',
        'rating',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'security/res_groups.xml',
        
        # Data
        'data/marketplace_data.xml',
        'data/mail_template_data.xml',
        
        # Views
        'views/marketplace_seller_views.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/marketplace_menus.xml',
        
        # Reports
    ],
    'demo': [
        'demo/marketplace_demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

