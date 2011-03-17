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
    'name': 'Membership',
    'version': '0.1',
    'category': 'Tools',
    'description': """
This module allows you to manage all operations for managing memberships.
It supports different kind of members:
* Free member
* Associated member (ex: a group subscribe for a membership for all
  subsidiaries)
* Paid members,
* Special member prices, ...

It is integrated with sales and accounting to allow you to automatically
invoice and send propositions for membership renewal.
    """,
    'author': 'OpenERP SA',
    'depends': ['base', 'product', 'account', 'process'],
    'init_xml': ['membership_data.xml'],
    'update_xml': [
        'security/ir.model.access.csv',
        'wizard/membership_invoice_view.xml',
        'membership_view.xml',
        'report/report_membership_view.xml',
        'process/membership_process.xml'
    ],
    'demo_xml': ['membership_demo.xml'],
    'test': ['test/test_membership.yml'],
    'installable': True,
    'active': False,
    'certificate': '0042907796381',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
