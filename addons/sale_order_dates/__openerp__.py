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
    'name': 'Dates on Sales Order',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
Add additional date information to the sales order.
===================================================

You can add the following additional dates to a sale order:
    * Requested Date
    * Commitment Date
    * Effective Date
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ["images/sale_order_dates.jpeg"],
    'depends': ["sale_stock"],
    'init_xml': [
    ],

    'update_xml': [
        'sale_order_dates_view.xml',
    ],
    'demo_xml': [
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'certificate' : '00867497685972962845',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
