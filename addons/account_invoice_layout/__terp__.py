# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'account_invoice_layout',
    'version': '1.0',
    'category': 'Generic Modules/Projects & Services',
    'description': """
    This module provides some features to improve the layout of the invoices.

    It gives you the possibility to
        * order all the lines of an invoice
        * add titles, comment lines, sub total lines
        * draw horizontal lines and put page breaks

    Moreover, there is one option which allow you to print all the selected invoices with a given special message at the bottom of it. This feature can be very useful for printing your invoices with end-of-year wishes, special punctual conditions...

    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'account'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'account_invoice_layout_view.xml',
        'account_invoice_layout_report.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0057235078173',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
