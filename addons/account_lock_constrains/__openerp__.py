# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Irreversible Lock Date',
    'version' : '1.0',
    'category': 'Accounting',
    'description': """
    Make the lock date irreversible:

    - The lock date for advisors must be higher of equals of the lock date for users.
    - The lock date for advisors must be higher of the last day of previous month.
    - The lock date for advisors must be strictly higher of the previous one.
    """,
    'depends' : ['account'],
    'data': [],
}
