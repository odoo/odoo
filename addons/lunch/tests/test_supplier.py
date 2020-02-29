# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from datetime import datetime
from unittest.mock import patch

from odoo import fields

from odoo.addons.lunch.tests.common import TestsCommon


class TestSupplier(TestsCommon):
    def setUp(self):
        super(TestSupplier, self).setUp()

        self.monday_1am = datetime(2018, 10, 29, 1, 0, 0)
        self.monday_10am = datetime(2018, 10, 29, 10, 0, 0)
        self.monday_1pm = datetime(2018, 10, 29, 13, 0, 0)
        self.monday_8pm = datetime(2018, 10, 29, 20, 0, 0)

        self.saturday_3am = datetime(2018, 11, 3, 3, 0, 0)
        self.saturday_10am = datetime(2018, 11, 3, 10, 0, 0)
        self.saturday_1pm = datetime(2018, 11, 3, 13, 0, 0)
        self.saturday_8pm = datetime(2018, 11, 3, 20, 0, 0)

    def test_compute_available_today(self):
        tests = [(self.monday_1am, True), (self.monday_10am, True),
                 (self.monday_1pm, True), (self.monday_8pm, True),
                 (self.saturday_3am, False), (self.saturday_10am, False),
                 (self.saturday_1pm, False), (self.saturday_8pm, False)]

        for value, result in tests:
            with patch.object(fields.Datetime, 'now', return_value=value) as _:
                assert self.supplier_pizza_inn.available_today == result,\
                    'supplier pizza inn should %s considered available on %s' % ('be' if result else 'not be', value)

            self.env['lunch.supplier'].invalidate_cache(['available_today'], [self.supplier_pizza_inn.id])

    def test_search_available_today(self):
        '''
            This test checks that _search_available_today returns a valid domain
        '''
        self.env.user.tz = 'Europe/Brussels'
        Supplier = self.env['lunch.supplier']

        tests = [(self.monday_1am, 1.0, 'monday'), (self.monday_10am, 10.0, 'monday'),
                 (self.monday_1pm, 13.0, 'monday'), (self.monday_8pm, 20.0, 'monday'),
                 (self.saturday_3am, 3.0, 'saturday'), (self.saturday_10am, 10.0, 'saturday'),
                 (self.saturday_1pm, 13.0, 'saturday'), (self.saturday_8pm, 20.0, 'saturday')]

        # It should return an empty domain if we compare to values other than datetime
        assert Supplier._search_available_today('>', 7) == []
        assert Supplier._search_available_today('>', True) == []

        for value, rvalue, dayname in tests:
            with patch.object(fields.Datetime, 'now', return_value=value) as _:
                assert Supplier._search_available_today('=', True) == ['&', '|', ('recurrency_end_date', '=', False),
                        ('recurrency_end_date', '>', value.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(self.env.user.tz))),
                        ('recurrency_%s' % (dayname), '=', True)],\
                        'Wrong domain generated for values (%s, %s)' % (value, rvalue)

        with patch.object(fields.Datetime, 'now', return_value=self.monday_10am) as _:
            assert self.supplier_pizza_inn in Supplier.search([('available_today', '=', True)])

    def test_auto_email_send(self):
        with patch.object(fields.Datetime, 'now', return_value=self.monday_1pm) as _:
            with patch.object(fields.Date, 'today', return_value=self.monday_1pm.date()) as _:
                with patch.object(fields.Date, 'context_today', return_value=self.monday_1pm.date()) as _:
                    line = self.env['lunch.order'].create({
                        'product_id': self.product_pizza.id,
                        'date': self.monday_1pm.date()
                    })

                    line.action_order()
                    assert line.state == 'ordered'

                    self.supplier_pizza_inn._auto_email_send()

                    assert line.state == 'confirmed'

                    line = self.env['lunch.order'].create({
                        'product_id': self.product_pizza.id,
                        'topping_ids_1': [(6, 0, [self.topping_olives.id])],
                        'date': self.monday_1pm.date()
                    })
                    line2 = self.env['lunch.order'].create({
                        'product_id': self.product_sandwich_tuna.id,
                        'date': self.monday_1pm.date()
                    })

                    (line | line2).action_order()
                    assert line.state == 'ordered'
                    assert line2.state == 'ordered'

                    self.supplier_pizza_inn._auto_email_send()

                    assert line.state == 'confirmed'
                    assert line2.state == 'ordered'

                    line_1 = self.env['lunch.order'].create({
                        'product_id': self.product_pizza.id,
                        'quantity': 2,
                        'date': self.monday_1pm.date()
                    })

                    line_2 = self.env['lunch.order'].create({
                        'product_id': self.product_pizza.id,
                        'topping_ids_1': [(6, 0, [self.topping_olives.id])],
                        'date': self.monday_1pm.date()
                    })

                    line_3 = self.env['lunch.order'].create({
                        'product_id': self.product_sandwich_tuna.id,
                        'quantity': 2,
                        'date': self.monday_1pm.date()
                    })

                    (line_1 | line_2 | line_3).action_order()

                    assert all(line.state == 'ordered' for line in [line_1, line_2, line_3])

                    self.supplier_pizza_inn._auto_email_send()
