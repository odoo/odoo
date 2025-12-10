# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMART Social Scheduler',
    'version': '18.0.1.0.0',
    'category': 'Sales/Marketplace',
    'summary': 'Social media post scheduling and queue management',
    'description': """
SMART Social Scheduler Module
=============================

This module handles:
- Social media post queue management
- Scheduled posting to Facebook, Instagram, TikTok, LinkedIn, WhatsApp
- Post status tracking
- Retry logic for failed posts
    """,
    'depends': [
        'smart_marketplace_core',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/social_post_queue_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
