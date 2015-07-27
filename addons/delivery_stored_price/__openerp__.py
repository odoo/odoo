# -*- coding: utf-8 -*-
{
    'name': 'Delivery Stored Price (saas-6 fix)',
    'version': '0.1',
    'category': 'Technical Settings',
    'description': """
Store delivery price on sale order without upgrading delivery module
====================================================================

This module is needed because we cannot add a column in stable saas-6 and has to be removed in master

""",
    'author': 'Odoo SA',
    'depends': ['delivery'],
    'installable': True,
    'auto_install': True,
}
