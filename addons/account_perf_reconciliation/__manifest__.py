# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Reconciliation Performance Fix',
    'version': '1.0',
    'summary': 'Precalculate some expressions of the reconciliation query in order to speed it up.',
    'description': """
Reconciliation Performance Fix
==============================
Always prefer to upgrade to version 14.0 or above instead of installing this module, if possible.
Installing this module will take a few minutes, install it outside working hours.

Depending on your accounting data volume and content, the reconciliation might be slow or even time out.
This module adds fields to precalculate and store expressions used by the reconciliation.
This means the reconciliation itself has less work to do and becomes faster.
Depending on your data, gains could be as much as a factor of 10.
    """,
    'category': 'Accounting/Accounting',
    'depends': ['account']
}
