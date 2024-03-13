# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Approvals Base',
    'version': '17.0.0',
    'category': 'Human Resources/Approvals',
    'description': """
        This module calculate the duration this approval request takes to be done
    """,
    'depends': ['approvals', 'project', 'base'],
    'data': [
        "security/security_views.xml",
        "views/approval_request_views.xml"
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
