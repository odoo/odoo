# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Jumana Jabin MP(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'Add Multiple Products To Invoice/Bill',
    'version': '16.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Easily add multiple products to a invoice/bill directly from '
               'the product views',
    'description': """This module allow you to add multiple products to the 
     corresponding invoice/bill. You can see all products in kanban, list and
     form view.You can also view the recent invoice/bill  history of the 
     selected product along with the option to update the quantity, 
     Change price, Add Multiple Products""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/product_product_views.xml',
        'wizard/invoice_product_details_views.xml'
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False
}
