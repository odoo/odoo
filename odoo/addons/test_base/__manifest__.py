# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'test_base',
    'category': 'Tests',
    'description': """A module to test orm, api, expression features.""",
    'depends': ['base'],
    'version': '0.0.1',
    'data': [
        'data/test_data.xml',
        'security/ir.model.access.csv',
    ]
}
