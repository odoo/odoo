# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<http://openerp.com>).
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
    'version': '0.1',
    'category': 'Tools',
    'description': """
This module allow you to send your documents via postal ways, thanks to Docsaway.
=================================================================================
    """,
    'author': 'OpenERP SA',
    'depends': ['sale','account'],
    'data': [
        'mail_docsaway_view.xml',
        'res_config_view.xml',
        'wizard/confirm_single_wizard.xml',
        'wizard/confirm_multiple_wizard.xml',
        'wizard/send_customer_post_wizard.xml',
        'security/ir.model.access.csv',
        'views/account_invoice_view.xml',
        'views/sale_view.xml',
    ],
    'installable': True,
    'auto_install': True,
}
