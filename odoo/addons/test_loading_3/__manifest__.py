# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'test-loading-3',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to test the registry loading/upgrading/installing feature.""",
    'depends': ['test_loading_1'],
    'data': ['data/test_loading_3_data.xml'],
    'installable': True,
    'pre_init_hook': 'pre_init_hook',
    'license': 'LGPL-3',
}
