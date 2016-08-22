# -*- coding: utf-8 -*-
###############################################################################
#
#   connector-ecommerce for OpenERP
#   Copyright (C) 2013-TODAY Akretion <http://www.akretion.com>.
#     @author Sébastien BEAU <sebastien.beau@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import mock

from openerp.addons.connector_ecommerce.unit.sale_order_onchange import (
    SaleOrderOnChange)
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.connector import Environment
import openerp.tests.common as common

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


class TestOnchange(common.TransactionCase):
    """ Test if the onchanges are applied correctly on a sales order"""

    def setUp(self):
        super(TestOnchange, self).setUp()
        self.session = ConnectorSession(self.cr, self.uid)

    def test_play_onchange(self):
        """ Play the onchange ConnectorUnit on a sales order """
        product_model = self.env['product.product']
        partner_model = self.env['res.partner']
        tax_model = self.env['account.tax']
        payment_method_model = self.env['payment.method']

        backend_record = mock.Mock()
        env = Environment(backend_record, self.session, 'sale.order')

        partner = partner_model.create({'name': 'seb',
                                        'zip': '69100',
                                        'city': 'Villeurbanne'})
        partner_invoice = partner_model.create({'name': 'Guewen',
                                                'zip': '1015',
                                                'city': 'Lausanne',
                                                'type': 'invoice',
                                                'parent_id': partner.id})
        tax = tax_model.create({'name': 'My Tax'})
        product = product_model.create({'default_code': 'MyCode',
                                        'name': 'My Product',
                                        'weight': 15,
                                        'taxes_id': [(6, 0, [tax.id])]})
        payment_term = self.env.ref('account.account_payment_term_advance')
        payment_method = payment_method_model.create({
            'name': 'Cash',
            'payment_term_id': payment_term.id,
        })

        order_vals = {
            'name': 'mag_10000001',
            'partner_id': partner.id,
            'payment_method_id': payment_method.id,
            'order_line': [
                (0, 0, {'product_id': product.id,
                        'price_unit': 20,
                        'name': 'My Real Name',
                        'product_uom_qty': 1,
                        'sequence': 1,
                        }
                 ),
            ],
            # fake field for the lines coming from a backend
            'backend_order_line': [
                (0, 0, {'product_id': product.id,
                        'price_unit': 10,
                        'name': 'Line 2',
                        'product_uom_qty': 2,
                        'sequence': 2,
                        }
                 ),
            ],
        }

        extra_lines = order_vals['backend_order_line']

        onchange = SaleOrderOnChange(env)
        order = onchange.play(order_vals, extra_lines)

        self.assertEqual(order['partner_invoice_id'], partner_invoice.id)
        self.assertEqual(order['payment_term'], payment_term.id)
        self.assertEqual(len(order['order_line']), 1)
        line = order['order_line'][0][2]
        self.assertEqual(line['name'], 'My Real Name')
        self.assertEqual(line['th_weight'], 15)
        self.assertEqual(line['tax_id'], [(6, 0, [tax.id])])
        line = order['backend_order_line'][0][2]
        self.assertEqual(line['name'], 'Line 2')
        self.assertEqual(line['th_weight'], 30)
        self.assertEqual(line['tax_id'], [(6, 0, [tax.id])])
