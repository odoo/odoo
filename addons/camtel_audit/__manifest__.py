# -*- coding: utf-8 -*-
{
    'name': 'CAMTEL Audit Logging',
    'version': '19.0.1.1.0',
    'category': 'Tools',
    'summary': 'Comprehensive audit logging for warehouse operations, purchases, logins, and permission changes',
    'description': """
CAMTEL Audit Logging Module
============================

This module provides comprehensive audit logging capabilities for CAMTEL warehouse operations:

Features:
---------
* Login/Logout event tracking (Odoo 19+ compatible)
* Inventory operations tracking (stock pickings, moves, adjustments)
* Purchase order tracking (creation, approval, modifications)
* Permission and access rights modification tracking
* User and group management tracking
* Detailed audit trail with user, timestamp, and change details
* Advanced filtering and search capabilities
* Export functionality for compliance reporting

All critical warehouse and system operations are automatically logged for auditing purposes.

Version 19.0.1.1.0 Changes:
---------------------------
* Fixed authentication API compatibility with Odoo 19
* Updated _login() and authenticate() methods to use new credential-based API
    """,
    'author': 'CAMTEL',
    'depends': [
        'base',
        'stock',
        'purchase',
        'web',
    ],
    'data': [
        'security/audit_security.xml',
        'security/ir.model.access.csv',
        'views/audit_log_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'camtel_audit/static/src/css/audit_log.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
