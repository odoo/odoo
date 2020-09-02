# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Manufacturing Test',
    'version': '2.0',
    'website': 'https://www.odoo.com/page/manufacturing',
    'category': 'Hidden',
    'summary': 'Manufacturing Test for cache issues',
    'description': """This module contains tests related to manufacturing.
Those are contained in a separate module as the standard `mrp.production`
model is inherited to reproduce an issue with cache management.""",
    'depends': ['mrp'],
    'data': [],
    'demo': [],
    'test': [],
    'installable': True,
    'application': False,
}
