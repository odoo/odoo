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
    'name': 'FIFO/LIFO stock valuation',
    'version': '0.1',
    'author': 'OpenERP SA',
    'summary': 'Valorize your stock FIFO/LIFO',
    'description' : """
Manage FIFO/LIFO stock valuation
================================

This gives reports which value the stock in a FIFO/LIFO way.  It adds a table to match the outs with the ins.  
    """,
    'website': 'http://www.openerp.com',
    'images': [],
    'depends': ['purchase'],
    'category': 'Warehouse Management',
    'sequence': 16,
    'demo': [
    ],
    'data': ['security/ir.model.access.csv'
    ],
    'test': ['test/fifolifo_price.yml', 
             'test/lifo_price.yml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'css': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
