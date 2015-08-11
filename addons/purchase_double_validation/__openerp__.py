# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Double Validation on Purchases',
    'version' : '1.1',
    'category': 'Purchase Management',
    'depends' : ['base','purchase'],
    'description': """
Double-validation for purchases exceeding minimum amount.
=========================================================

This module modifies the purchase workflow in order to validate purchases that
exceeds minimum amount set by configuration wizard.
    """,
    'website': 'https://www.odoo.com/page/purchase',
    'data': [
        'purchase_double_validation_workflow.xml',
        'purchase_double_validation_installer.xml',
        'purchase_double_validation_view.xml',
    ],
    'test': [
        'test/purchase_double_validation_demo.yml',
        'test/purchase_double_validation_test.yml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False
}
