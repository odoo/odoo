# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.tests import tagged
from odoo.fields import Command

from odoo.addons.test_event_full.tests.common import TestEventFullCommon


@tagged('post_install', '-at_install')
class TestEventTicketPriceRounding(TestEventFullCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ticket_product.write({
            'lst_price': 1.0
        })

        cls.currency_jpy = cls.env['res.currency'].create({
            'name': 'JPX',
            'symbol': '¥',
            'rounding': 1.0,
            'rate_ids': [Command.create({'rate': 133.6200, 'name': time.strftime('%Y-%m-%d')})],
        })

        cls.currency_cad = cls.env['res.currency'].create({
            'name': 'CXD',
            'symbol': '$',
            'rounding': 0.01,
            'rate_ids': [Command.create({'rate': 1.338800, 'name': time.strftime('%Y-%m-%d')})],
        })

        cls.pricelist_usd = cls.env['product.pricelist'].create({
            'name': 'Pricelist USD',
            'currency_id': cls.env.ref('base.USD').id,
        })

        cls.pricelist_jpy = cls.env['product.pricelist'].create({
            'name': 'Pricelist JPY',
            'currency_id': cls.currency_jpy.id,
        })

        cls.pricelist_cad = cls.env['product.pricelist'].create({
            'name': 'Pricelist CAD',
            'currency_id': cls.currency_cad.id,
        })

        cls.event_type = cls.env['event.type'].create({
            'name': 'Test Event Type',
            'auto_confirm': True,
            'event_type_ticket_ids': [
                (0, 0, {
                    'name': 'Test Event Ticket',
                    'product_id': cls.ticket_product.id,
                    'price': 30.0,
                })
            ],
        })

        cls.event_ticket = cls.event_type.event_type_ticket_ids[0]

    def test_no_discount_usd(self):
        ticket = self.event_ticket.with_context(pricelist=self.pricelist_usd.id)
        ticket._compute_price_reduce()
        self.assertAlmostEqual(ticket.price_reduce, 30.0, places=6, msg="No discount should be applied for the USD pricelist.")

    def test_no_discount_jpy(self):
        ticket = self.event_ticket.with_context(pricelist=self.pricelist_jpy.id)
        ticket._compute_price_reduce()
        self.assertAlmostEqual(ticket.price_reduce, 30.0, places=6, msg="No discount should be applied for the JPY pricelist.")

    def test_no_discount_cad(self):
        ticket = self.event_ticket.with_context(pricelist=self.pricelist_cad.id)
        ticket._compute_price_reduce()
        self.assertAlmostEqual(ticket.price_reduce, 30.0, places=6, msg="No discount should be applied for the CAD pricelist.")
