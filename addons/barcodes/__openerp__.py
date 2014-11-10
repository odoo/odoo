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
    'name': 'Advanced Barcodes',
    'version': '1.0',
    'category': '',
    'sequence': 6,
    'summary': 'Advanced Barcode Setup',
    'description': """

=======================

This module unlocks several advanced barcode features:

- Barcode aliases allows you to identify the same product with different barcodes
- Barcode patterns to identify e.g. customers, employees, weighted, discounted and custom priced products
- Unlimited barcode patterns and definitions. 

""",
    'author': 'OpenERP SA',
    'depends': [],
    'website': '',
    'data': [
        'data/barcodes_data.xml',
        'barcodes_view.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
