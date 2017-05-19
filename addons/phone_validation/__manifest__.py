# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Phone Numbers Validation',
    'summary': 'Validate and format phone numbers',
    'sequence': '9999',
    'category': 'Hidden',
    'description': """
Phone Numbers Validation
========================

This module adds the feature of validation and formatting phone numbers
according to a destination country. It also handles national and international
formatting.

This module applies this feature to Leads and Contacts.""",
    'data': [
    ],
    'depends': ['base'],
}
