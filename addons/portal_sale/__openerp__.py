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
    'name': 'Portal Sale',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description': """
This module adds a Sales menu to your portal as soon as sale and portal are installed.
======================================================================================

After installing this module, portal users will be able to access their own documents
via the following menus:

  - Quotations
  - Sale Orders
  - Delivery Orders
  - Products (public ones)
  - Invoices
  - Payments/Refunds

If online payment acquirers are configured, portal users will also be given the opportunity to
pay online on their Sale Orders and Invoices that are not paid yet. Paypal is included
by default, you simply need to configure a Paypal account in the Accounting/Invoicing settings.
    """,
    'author': 'OpenERP SA',
    'depends': ['sale','portal'],
    'data': [
        'security/portal_security.xml',
        'portal_sale_view.xml',
        'portal_sale_data.xml',
        'res_config_view.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': True,
    'category': 'Hidden',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
