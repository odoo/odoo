# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Phone Numbers Validation',
    'version': '2.0',
    'summary': 'Validate and format phone numbers',
    'sequence': '9999',
    'category': 'Hidden',
    'description': """
Phone Numbers Validation
========================

This module adds the feature of validation and formatting phone numbers
according to a destination country.

It also adds phone blacklist management through a specific model storing
blacklisted phone numbers.

It adds two mixins :

  * phone.validation.mixin: parsing / formatting helpers on records, to be
    used for example in number fields onchange;
  * mail.thread.phone: handle sanitation and blacklist of records numbers;
""",
    'data': [
        'security/ir.model.access.csv',
        'views/phone_blacklist_views.xml',
    ],
    'depends': [
        'base',
        'mail',
    ],
    'auto_install': True,
}
