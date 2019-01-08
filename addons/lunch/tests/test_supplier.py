# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch

from odoo import fields

from odoo.addons.lunch.tests.common import TestsCommon


class TestSupplier(TestsCommon):
    def setUp(self):
        super(TestSupplier, self).setUp()

        self.monday_3am = datetime(2018, 10, 29, 3, 0, 0)
        self.monday_10am = datetime(2018, 10, 29, 10, 0, 0)
        self.monday_1pm = datetime(2018, 10, 29, 13, 0, 0)
        self.monday_8pm = datetime(2018, 10, 29, 20, 0, 0)

        self.saturday_3am = datetime(2018, 11, 3, 3, 0, 0)
        self.saturday_10am = datetime(2018, 11, 3, 10, 0, 0)
        self.saturday_1pm = datetime(2018, 11, 3, 13, 0, 0)
        self.saturday_8pm = datetime(2018, 11, 3, 20, 0, 0)

    def test_compute_available_today(self):
        tests = [(self.monday_3am, False), (self.monday_10am, True),
                 (self.monday_1pm, True), (self.monday_8pm, True),
                 (self.saturday_3am, False), (self.saturday_10am, False),
                 (self.saturday_1pm, False), (self.saturday_8pm, False)]

        for value, result in tests:
            with patch.object(fields.Datetime, 'now', return_value=value) as _:
                assert self.supplier_pizza_inn.available_today == result,\
                    'supplier pizza inn should %s considered available on %s' % ('be' if result else 'not be', value)

            self.env['lunch.supplier'].invalidate_cache(['available_today'], [self.supplier_pizza_inn.id])

    def test_search_available_today(self):
        Supplier = self.env['lunch.supplier']

        tests = [(self.monday_3am, 3.0, 'monday'), (self.monday_10am, 10.0, 'monday'),
                 (self.monday_1pm, 13.0, 'monday'), (self.monday_8pm, 20.0, 'monday'),
                 (self.saturday_3am, 3.0, 'saturday'), (self.saturday_10am, 10.0, 'saturday'),
                 (self.saturday_1pm, 13.0, 'saturday'), (self.saturday_8pm, 20.0, 'saturday')]

        assert Supplier._search_available_today('>', 7) == []
        assert Supplier._search_available_today('>', True) == []

        for value, rvalue, dayname in tests:
            with patch.object(fields.Datetime, 'now', return_value=value) as _:
                assert Supplier._search_available_today('=', True) == ['|', '&', '&', ('recurrency', '=', 'once'), ('recurrency_date_from', '<=', value),
                    ('recurrency_date_to', '>=', value), '&', '&', ('recurrency_%s' % (dayname), '=', True),
                    ('recurrency_from', '<=', rvalue), ('recurrency_to', '>=', rvalue)], 'Wrong domain generated for values (%s, %s)' % (value, rvalue)

            assert self.supplier_pizza_inn in Supplier.search([('available_today', '=', True)])

    def test_auto_email_send(self):
        order = self.env['lunch.order'].create({})
        line = self.env['lunch.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_pizza.id,
        })

        assert len(order.supplier_ids) == 1 and self.supplier_pizza_inn in order.supplier_ids

        order.action_order()
        assert order.state == 'ordered'
        assert line.state == 'ordered'

        with patch.object(fields.Datetime, 'now', return_value=self.monday_1pm):
            with patch.object(fields.Date, 'today', return_value=self.monday_1pm.date()):
                self.supplier_pizza_inn._auto_email_send()

        assert order.state == 'confirmed'
        assert line.state == 'confirmed'
        assert order.mail_sent

        # Do the same but this time order contains multiple lines with products from at least two suppliers
        # Check if the lines for pizza_inn have been sent, and put in state='confirmed' only those lines should be
        # moreover the order should not yet be in state='confirmed' as there still are some lines to confirm
        order = self.env['lunch.order'].create({})
        line = self.env['lunch.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_pizza.id,
            'topping_ids': [(6, 0, [self.topping_olives.id])],
        })
        line2 = self.env['lunch.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_sandwich_tuna.id,
        })

        assert len(order.supplier_ids) == 2 and self.supplier_coin_gourmand in order.supplier_ids and self.supplier_pizza_inn in order.supplier_ids

        order.action_order()
        assert order.state == 'ordered'
        assert line.state == 'ordered'
        assert line2.state == 'ordered'

        with patch.object(fields.Datetime, 'now', return_value=self.monday_1pm):
            with patch.object(fields.Date, 'today', return_value=self.monday_1pm.date()):
                self.supplier_pizza_inn._auto_email_send()

        assert order.state == 'confirmed'
        assert line.state == 'confirmed'
        assert line2.state == 'ordered'

        assert order.mail_sent

        # Check with multiple orders
        order_1 = self.env['lunch.order'].create({})

        line_1_1 = self.env['lunch.order.line'].create({
            'order_id': order_1.id,
            'product_id': self.product_pizza.id,
        })

        line_1_2 = line_1_1 = self.env['lunch.order.line'].create({
            'order_id': order_1.id,
            'product_id': self.product_pizza.id,
            'topping_ids': [(6, 0, [self.topping_olives.id])]
        })

        order_2 = self.env['lunch.order'].create({})

        line_2_1 = self.env['lunch.order.line'].create({
            'order_id': order_2.id,
            'product_id': self.product_sandwich_tuna.id
        })

        line_2_2 = self.env['lunch.order.line'].create({
            'order_id': order_2.id,
            'product_id': self.product_pizza.id,
        })

        order_3 = self.env['lunch.order'].create({})

        line_3_1 = self.env['lunch.order.line'].create({
            'order_id': order_3.id,
            'product_id': self.product_sandwich_tuna.id
        })

        (order_1 | order_2 | order_3).action_order()

        assert all(order.state == 'ordered' for order in [order_1, order_2, order_3])
        assert all(line.state == 'ordered' for line in [line_1_1, line_1_2, line_2_1, line_2_2, line_3_1])

        with patch.object(fields.Datetime, 'now', return_value=self.monday_1pm):
            with patch.object(fields.Date, 'today', return_value=self.monday_1pm.date()):
                self.supplier_pizza_inn._auto_email_send()

        assert all(order.state == 'confirmed' for order in [order_1, order_2])
        assert order_3.state == 'ordered'
        assert all(line.state == 'confirmed' for line in [line_1_1, line_1_2, line_2_2])
        assert all(line.state == 'ordered' for line in [line_2_1, line_3_1])

        assert all(order.mail_sent for order in [order_1, order_2])
        assert not order_3.mail_sent
