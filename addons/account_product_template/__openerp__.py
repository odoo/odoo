# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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
    'name': 'Product Email Template',
    'depends': ['account'],
    'author': 'OpenERP SA',
    'category': 'Accounting & Finance',
    'description': """
Add email templates to products to be send on invoice confirmation
==================================================================

With this module, link your products to a template to send complete information and tools to your customer.
For instance when invoicing a training, the training agenda and materials will automatically be send to your customers.'
    """,
    'website': 'http://www.openerp.com',
    'demo': [
        'account_product_template_demo.xml',
    ],
    'data': [
        'account_product_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
