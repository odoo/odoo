# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "Accounting and Finance",
    "version" : "1.1",
    "author" : "OpenERP SA",
    "category": 'Accounting & Finance',
    "sequence": 10,
    "description": """
Accounting Access Rights.
=========================

This module gives the Admin user the access to all the accounting features
like the journal items and the chart of accounts.

It assigns manager and user access rights to the Administrator, and only
user rights to Demo user.
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    "depends" : ["account_voucher"],
    'update_xml': [
        'security/account_security.xml',
        'account_accountant_data.xml'
    ],
    'demo_xml': ['account_accountant_demo.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'certificate': '00395091383933390541',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
