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
    'name' : 'Analytic Accounting',
    'version': '1.1',
    'author' : 'OpenERP SA',
    'website' : 'http://www.openerp.com',
    'category': 'Hidden/Dependency',
    'depends' : ['base', 'decimal_precision', 'mail'],
    'description': """
Module for defining analytic accounting object.
===============================================

In OpenERP, analytic accounts are linked to general accounts but are treated
totally independently. So, you can enter various different analytic operations
that have no counterpart in the general financial accounts.
    """,
    'data': [
        'security/analytic_security.xml',
        'security/ir.model.access.csv',
        'analytic_sequence.xml',
        'analytic_view.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'certificate' : '00462253285027988541',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
