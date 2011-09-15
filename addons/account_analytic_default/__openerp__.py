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
    'name'      : 'Account Analytic Defaults',
    'version'   : '1.0',
    'category'  : 'Finance',
    'complexity': "normal",
    'description': """Set default values for your analytic accounts
Allows to automatically select analytic accounts based on criterions:
=====================================================================

* Product
* Partner
* User
* Company
* Date
    """,
    'author'    : 'OpenERP SA',
    'website'   : 'http://www.openerp.com',
    'images'   : ['images/analytic_defaults.jpeg'],
    'depends'   : ['sale'],
    'init_xml'  : [],
    'update_xml': ['security/ir.model.access.csv', 'account_analytic_default_view.xml'],
    'demo_xml'  : [],
    'installable': True,
    'active': False,
    'certificate': '0074229833581',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
