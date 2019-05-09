# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com)

{
    'name': 'Argentina - Accounting',
    'version': '12.0.1.0.0',
    'description': """
Test L10N AR
============

Dummt module that only try to change the res.company country in order to be
able to install the argentinian localizarion in runbot by default.

NOTE: Delete this module before merge
""",
    'author': ['ADHOC SA'],
    'category': 'Localization',
    'depends': [
        'base',
    ],
    'data':[
    ],
    'demo': [
    ],
    'post_init_hook': 'post_init_hook',
    'auto_install': True,
}
