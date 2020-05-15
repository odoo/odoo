# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.addons.event_sale.tests.common import TestEventSaleCommon


class TestEventCrmSaleCommon(TestEventCrmCommon, TestEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventCrmSaleCommon, cls).setUpClass()

        cls.event_0.write({
            'event_ticket_ids': [
                (5, 0),
                (0, 0, {
                    'name': 'First Ticket',
                    'product_id': cls.event_product.id,
                    'seats_max': 30,
                }), (0, 0, {
                    'name': 'Second Ticket',
                    'product_id': cls.event_product.id,
                })
            ],
        })
