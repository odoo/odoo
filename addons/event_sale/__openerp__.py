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
    'name': 'Events Sales',
    'version': '0.1',
    'category': 'Tools',
    'complexity': "easy",
    'description': """
    Creating registration with sale orders
    ==========================================

    With this module you are able to create a registration when you create a sale order where the product is event type.

    Note that: 
        -you can create event object. In product when you choose event you can match with an event type
        -if you select an event prduct in a sale order line you can linked to an existing event
        -when you confirm your sale order it will automatically create a registration for this event
""",
    'author': 'OpenERP SA',
    'depends': ['event','sale','sale_crm'],
    'update_xml': [
        'sale_order_view.xml',
    ],
    'test':['test/confirm.yml'],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
