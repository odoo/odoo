# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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
    'name': 'Payment: Website Integration (Test Module)',
    'category': 'Website',
    'summary': 'Payment: Website Integration (Test Module)',
    'version': '1.0',
    'description': """Module installing all sub-payment modules and adding some
    controllers and menu entries in order to test them.""",
    'author': 'OpenERP SA',
    'depends': [
        'website',
        'payment_acquirer',
        'payment_acquirer_ogone',
        'payment_acquirer_paypal',
        'payment_acquirer_transfer',
    ],
    'data': [
        'views/website_payment_templates.xml',
    ],
    'installable': True,
}
