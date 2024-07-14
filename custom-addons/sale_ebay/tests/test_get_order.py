# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch, Mock

from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .test_data import EBAY_ANSWER_1

class TestEbay(TransactionCase):
    def setUp(self):
        # we just want the response eBay gives us to have a method 'dict' that actually contains the data
        # e.g. we do response = self._ebay_execute('GetOrders', call_data); order_dict = response.dict()
        def fake_execute_data(data):
            class X(object):
                def dict(self):
                    return data
            def fake_execute(*_args, **_kwargs):
                return X()
            return fake_execute

        self.fake_execute_data = fake_execute_data

        super(TestEbay, self).setUp()

    def test_synchronize_order(self):
        """Test importing two basic orders with three transactions."""
        with patch('odoo.addons.sale_ebay.models.product.ProductTemplate._ebay_execute',
                   new=self.fake_execute_data(EBAY_ANSWER_1)), patch('odoo.addons.sale_ebay.models.product.ProductTemplate._ebay_configured', new=lambda d: True):
            number_of_sos = []
            number_of_sos.append(self.env['sale.order'].search_count([]))
            # if an error happens during synchronisation, it will create a logging with name 'eBay'
            number_of_ebay_loggings = self.env['ir.logging'].search_count([('name', '=', 'eBay')])

            # the test data contains three orders (one order per transaction)
            # Orders are identified by an id, so provided the ids are not already in database
            # it should create matching ones within Odoo
            self.env['product.template'].synchronize_orders_from_last_sync()

            number_of_sos.append(self.env['sale.order'].search_count([]))
            self.assertEqual(number_of_sos[1], number_of_sos[0] + 3)

            # we do it a second time with the same answer;
            # it should not create any error, but it should not do anything new either
            number_of_sos.append(self.env['sale.order'].search_count([]))
            self.assertEqual(number_of_sos[2], number_of_sos[1])

            self.assertEqual(
                self.env['ir.logging'].search_count([('name', '=', 'eBay')]),
                number_of_ebay_loggings,
                "No new loggings should have been created."
            )
