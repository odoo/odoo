# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Crm Phone Numbers Validation',
    'summary': 'Validate and format phone numbers for leads and contacts',
    'sequence': '9999',
    'category': 'Hidden',
    'description': """
CRM Phone Numbers Validation
============================

This module allows for validate and format phone numbers for leads and contacts.""",
    'data': [
    ],
    'depends': [
        'phone_validation',
        'crm',
    ],
}
