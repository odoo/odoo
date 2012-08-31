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
    'description': """
Creating registration with sale orders.
=======================================

This module allows you to automatize and connect your registration creation with
your main sale flow and therefore, to enable the invoicing feature of registrations.

It defines a new kind of service products that offers you the possibility to
choose an event category associated with it. When you encode a sale order for
that product, you will be able to choose an existing event of that category and
when you confirm your sale order it will automatically create a registration for
this event.
""",
    'author': 'OpenERP SA',
    'depends': ['event','sale','sale_crm'],
    'data': ['event_sale_view.xml'],
    'demo': ['event_demo.xml'],
    'test': ['test/confirm.yml'],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
