# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'test-uninstall',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to test the uninstall feature.""",
    'depends': ['base'],
    'data': ['ir.model.access.csv'],
    'installable': True,
    'auto_install': False,
}
