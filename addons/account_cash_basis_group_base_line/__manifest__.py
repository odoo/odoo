# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Tax Cash Basis Group Base Lines',
    'version' : '1.0',
    'summary': 'Group base lines to minimize the number of lines in Cash Basis Journal Entry',
    'sequence': 5,
    'description': """
Instead of creating two base lines per line with cash basis tax, let us group the creation the Lines
so that there are fewer lines in the Cash Basis Journal Entry.
    """,
    'category': 'Accounting',
    'depends': ['account'],
    'data': [],
    'installable': True,
    'auto_install': False,
}
