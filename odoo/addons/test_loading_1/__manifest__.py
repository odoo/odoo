# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'test-loading-1',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to test the registry loading/upgrading/installing feature.""",
    'depends': ['test_loading'],
    'data': ['ir.model.access.csv', 'data/test_loading_1_data.xml'],
    'installable': True,
    'license': 'LGPL-3',
}
