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
    'name': 'Purchase Analytic Plans',
    'version': '1.0',
    'category': 'Purchase Management',
    'description': """
The base module to manage analytic distribution and purchase orders.
====================================================================

Allows the user to maintain several analysis plans. These let you split a line
on a supplier purchase order into several accounts and analytic plans.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images' : ['images/purchase_analytic_distribution.jpeg'],
    'depends': ['purchase', 'account_analytic_plans'],
    'data': [],
    'data': ['purchase_analytic_plans_view.xml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'certificate': '0062176518909',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
