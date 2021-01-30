# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Irreversible Lock Date',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
    Make the lock date irreversible:

    * You cannot set stricter restrictions on advisors than on users. Therefore, the All Users Lock Date must be anterior (or equal) to the Invoice/Bills Lock Date.
    * You cannot lock a period that has not yet ended. Therefore, the All Users Lock Date must be anterior (or equal) to the last day of the previous month.
    * Any new All Users Lock Date must be posterior (or equal) to the previous one.
    """,
    'depends': ['account'],
    'data': [],
}
