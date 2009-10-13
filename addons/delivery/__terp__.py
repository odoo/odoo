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
    'name': 'Carriers and deliveries',
    'version': '1.0',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """Allows you to add delivery methods in sales orders and packing. You can define your own carrier and delivery grids for prices. When creating invoices from picking, Open ERP is able to add and compute the shipping line.""",
    'author': 'Tiny',
    'depends': ['sale', 'purchase', 'stock'],
    'init_xml': ['delivery_data.xml'],
    'update_xml': [
        'security/ir.model.access.csv',
        'delivery_view.xml',
        'delivery_wizard.xml',
        'partner_view.xml'
    ],
    'demo_xml': ['delivery_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0033981912253',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
