# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.addons.event_product.tests.common import TestEventProductCommon
from odoo.addons.sales_team.tests.common import TestSalesCommon


class TestEventSaleCommon(TestEventProductCommon, TestSalesCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventSaleCommon, cls).setUpClass()

        cls.event_0 = cls.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
        })

    def _create_ticket_so(self, ticket, prices):
        """ Create a sale order with one line of the ticket per given price. """
        return self.env['sale.order'].create({
            'partner_id': self.event_customer.id,
            'order_line': [Command.create({
                'event_id': ticket.event_id.id,
                'event_ticket_id': ticket.id,
                'product_id': ticket.product_id.id,
                'price_unit': price,
            }) for price in prices],
        })
