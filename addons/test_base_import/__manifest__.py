# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test - Base Import',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 3843,
    'summary': 'Base Import Tests: Ensure Flow Robustness',
    'description': """This module contains tests related to base import.""",
    'depends': ['base_import'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
