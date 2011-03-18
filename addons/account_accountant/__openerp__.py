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
    "name" : "Accountant",
    "version" : "1.1",
    "author" : "OpenERP SA",
    "category": 'Generic Modules/Accounting',
    "description": """
This module gives the admin user the access to all the accounting features like the journal items and the chart of accounts.
============================================================================================================================
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    "depends" : ["account"],
    'update_xml': [
        'security/account_security.xml',
    ],
    'demo_xml': ['account_accountant_demo.xml'],
    'test': [],
    'installable': True,
    'active': False,
    'certificate': '00395091383933390541',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
