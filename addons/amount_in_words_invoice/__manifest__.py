# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Cybrosys Technologies (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL v3) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
{
    'name': "Amount In Words In Invoice, Sale Order And Purchase Order",
    'version': '16.0.1.0.0',
    'summary': """Showing the subtotal amounts of invoice, sale order and purchase order in words""",
    'description': """The Module to Shows The Subtotal Amount in Words on Invoice, Sale Order and Purchase Order""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'category': 'Accounting,Sales,Purchase',
    'depends': ['sale_management', 'account', 'purchase'],
    'data': [
        'data/credit_note_mail_template.xml',
        'data/invoice_mail_template.xml',
        'data/payment_mail_template.xml',
        'data/purchase_order_mail_template.xml',
        'data/sale_order_confirm_mail_template.xml',
        'data/sale_order_mail_template.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'report/reports.xml'
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
