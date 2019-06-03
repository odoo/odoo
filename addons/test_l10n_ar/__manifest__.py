# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Argentina Localization Test',
    'version': '12.0.1.0.0',
    'description': """
Test L10N AR
============

Dummy module that only try to install argentinian localization in runbot

NOTE: Delete this module before merge
""",
    'author': ['ADHOC SA'],
    'category': 'Localization',
    'depends': [
        'account',
    ],
    'data':[
    ],
    'demo': [
    ],
    'post_init_hook': 'post_init_hook',
    'auto_install': False,
}
