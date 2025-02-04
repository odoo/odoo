# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Phone Numbers Validation',
    'version': '2.1',
    'summary': 'Validate and format phone numbers',
    'sequence': 9999,
    'category': 'Hidden',
    'description': """
Phone Numbers Validation
========================

This module adds the feature of validation and formatting phone numbers
according to a destination country.

It also adds phone blacklist management through a specific model storing
blacklisted phone numbers.

It adds mail.thread.phone mixin that handles sanitation and blacklist of
records numbers. """,
    'data': [
        'security/ir.model.access.csv',
        'views/phone_blacklist_views.xml',
        'views/res_partner_views.xml',
        'wizard/phone_blacklist_remove_view.xml',
    ],
    'depends': [
        'base',
        'mail',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
