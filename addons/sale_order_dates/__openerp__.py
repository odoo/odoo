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
    'version': '1.1',
    'category': 'Sales Management',
    'description': """
Add additional date information to the sales order.
===================================================

You can add the following additional dates to a sales order:
------------------------------------------------------------
    * Requested Date (will be used as the expected date on pickings)
    * Commitment Date
    * Effective Date
""",
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sale_stock'],
    'data': ['sale_order_dates_view.xml'],
    'demo': [],
    'test': ['test/requested_date.yml'],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
