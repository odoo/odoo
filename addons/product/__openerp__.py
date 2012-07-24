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
    "name" : "Products & Pricelists",
    "version" : "1.1",
    "author" : "OpenERP SA",
    'category': 'Sales Management',
    "depends" : ["base", "process", "decimal_precision", "mail"],
    "init_xml" : [],
    "demo_xml" : ["product_demo.xml"],
    "description": """
This is the base module for managing products and pricelists in OpenERP.
========================================================================

Products support variants, different pricing methods, suppliers
information, make to stock/order, different unit of measures,
packaging and properties.

Pricelists support:
    * Multiple-level of discount (by product, category, quantities)
    * Compute price based on different criteria:
        * Other pricelist,
        * Cost price,
        * List price,
        * Supplier price, ...

Pricelists preferences by product and/or partners.

Print product labels with barcode.
    """,
    'update_xml': [
        'security/product_security.xml',
        'security/ir.model.access.csv',
        'wizard/product_price_view.xml',
        'product_data.xml',
        'product_report.xml',
        'product_view.xml',
        'product_shortcut_data.xml',
        'pricelist_view.xml',
        'partner_view.xml',
        'process/product_process.xml'
    ],
    'test': [
        'product_pricelist_demo.yml',
        'test/product_uom.yml',
        'test/product_pricelist.yml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': '0068861431437',
    'images': ['images/product_uom.jpeg','images/product_pricelists.jpeg','images/products_categories.jpeg', 'images/products_form.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
