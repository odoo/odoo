# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<https://www.odoo.com>).
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
    'name': 'Mail Docsaway Web Service',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module allows you to send your documents through postal mail, thanks to Docsaway.
======================================================================================
    """,
    'author': 'OpenERP SA',
    'depends': ['sale','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/print_docsaway_view.xml',
        'views/res_config_view.xml',
        'views/account_invoice_view.xml',
        'views/sale_view.xml',
        'wizard/confirm_single_wizard.xml',
        'wizard/confirm_multiple_wizard.xml',
        'wizard/send_customer_post_wizard.xml',
    ],
    'installable': True,
    'auto_install': True,
}
