# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on sales team (Manager)',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Mass mail - Blacklist access to Sales Manager
=============================================

Bridge module adding UX requirements to allow sales team manager to get access to blacklist.
        """,
    'depends': ['sales_team', 'mass_mailing'],
    'data': [
        'security/ir.model.access.csv'
    ],
    'auto_install': True,
}
