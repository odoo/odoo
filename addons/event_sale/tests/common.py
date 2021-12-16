# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.event.tests.common import EventCase
from odoo.addons.sales_team.tests.common import TestSalesCommon


class TestEventSaleCommon(EventCase, TestSalesCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventSaleCommon, cls).setUpClass()

        cls.event_product = cls.env['product.product'].create({
            'name': 'Test Registration Product',
            'description_sale': 'Mighty Description',
            'list_price': 10,
            'standard_price': 30.0,
            'detailed_type': 'event',
        })

        cls.event_type_tickets = cls.env['event.type'].create({
            'name': 'Update Type',
            'auto_confirm': True,
            'has_seats_limitation': True,
            'seats_max': 30,
            'default_timezone': 'Europe/Paris',
            'event_type_ticket_ids': [
                (0, 0, {'name': 'First Ticket',
                        'product_id': cls.event_product.id,
                        'seats_max': 5,
                       })
            ],
            'event_type_mail_ids': [],
        })

        cls.event_0 = cls.env['event.event'].create({
            'name': 'TestEvent',
            'auto_confirm': True,
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
        })
