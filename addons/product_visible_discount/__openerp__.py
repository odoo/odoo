##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Prices Visible Discounts',
    'version': '1.0',
    'author': 'OpenERP SA',
    'category': 'Sales Management',
    'website': 'https://www.odoo.com',
    'description': """
This module lets you calculate discounts on Sale Order lines and Invoice lines base on the partner's pricelist.
===============================================================================================================

To this end, a new check box named 'Visible Discount' is added to the pricelist form.

**Example:**
    For the product PC1 and the partner "Asustek": if listprice=450, and the price
    calculated using Asustek's pricelist is 225. If the check box is checked, we
    will have on the sale order line: Unit price=450, Discount=50,00, Net price=225.
    If the check box is unchecked, we will have on Sale Order and Invoice lines:
    Unit price=225, Discount=0,00, Net price=225.
    """,
    'depends': ["sale","purchase"],
    'demo': [],
    'data': ['product_visible_discount_view.xml'],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
