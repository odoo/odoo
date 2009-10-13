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
    'name': 'Invoice Picking Directly',
    'version': '1.0',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """
        When you send or deliver goods, this module automatically launch
        the invoicing wizard if the delivery is to be invoiced.
    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['delivery', 'stock'],
    'init_xml': [],
    'update_xml': [],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0081385081261',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
