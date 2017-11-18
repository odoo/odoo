# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Phone Numbers Validation',
    'summary': 'Validate and format phone numbers for leads and contacts',
    'sequence': '9999',
    'category': 'Hidden',
    'description': """
HR Phone Numbers Validation
============================

This module allows for validate and format phone numbers for Employee.""",
    'depends': [
        'phone_validation',
        'hr',
    ],
}
