# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Contact Form Number Validation',
    'summary': 'Validate and format contact form numbers',
    'sequence': '9999',
    'category': 'Hidden',
    'description': """
Contact Number Validation on Website
====================================

Validate contact (phone,mobile,fax) numbers and normalize them on leads and contacts:
- use the national format for your company country
- use the international format for all others
        """,
    'data': [],
    'depends': [
        'crm_phone_validation',
        'website_crm',
        'website_form',
    ],
    'auto_install': True,
}
