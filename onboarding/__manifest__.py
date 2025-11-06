# -*- coding: utf-8 -*-
{
    'name': 'VendAI Onboarding',
    'version': '1.0.0',
    'category': 'Point of Sale',
    'sequence': 1,
    'summary': 'Simplified onboarding experience for VendAI POS',
    'description': """
VendAI Onboarding Module
========================

This module provides a simplified, user-friendly onboarding experience for VendAI POS.
It replaces Odoo's overwhelming apps screen with a clean, guided setup wizard that focuses
only on essential POS functionality.

Features:
- Guided 4-step onboarding wizard
- Simplified app selection (only POS-relevant modules)
- VendAI branding and styling
- Consumer-app-like interface
- Automatic installation of essential modules
    """,
    'depends': ['base', 'web', 'point_of_sale', 'stock', 'purchase', 'account', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/vendai_data.xml',
        'views/vendai_onboarding_views.xml',
        'views/vendai_apps_views.xml',
        'views/res_config_settings_views.xml',
        'views/vendai_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'onboarding/static/src/scss/vendai_onboarding.scss',
            'onboarding/static/src/js/vendai_onboarding.js',
            'onboarding/static/src/js/vendai_apps_menu.js',
        ],
        'web.assets_frontend': [
            'onboarding/static/src/scss/vendai_frontend.scss',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'website': 'https://vendai.com',
    'license': 'LGPL-3',
}
