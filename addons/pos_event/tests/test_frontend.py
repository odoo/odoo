# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from datetime import timedelta
from odoo.fields import Datetime

import odoo.tests

class TestPosEventHttpCommon(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        env = cls.env

        cls.pos_user.write({
            'groups_id': [
                (4, env.ref('event.group_event_manager').id),
            ]
        })
        cls.event = env['event.event'].create({
            'name': 'Conference for Architects TEST',
            'user_id': env.ref('base.user_admin').id,
            'date_begin': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 07:00:00'),
            'date_end': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 16:30:00'),
            'available_in_pos': True,
        })

        env['event.event.ticket'].create([{
            'name': 'Standard',
            'event_id': cls.event.id,
            'product_id': env.ref('event_product.product_product_event').id,
            'start_sale_datetime': (Datetime.today() - timedelta(days=5)).strftime('%Y-%m-%d 07:00:00'),
            'end_sale_datetime': (Datetime.today() + timedelta(90)).strftime('%Y-%m-%d'),
            'price': 1000.0,
            'seats_max': 100,
        }, {
            'name': 'VIP',
            'event_id': cls.event.id,
            'product_id': env.ref('event_product.product_product_event').id,
            'end_sale_datetime': (Datetime.today() + timedelta(90)).strftime('%Y-%m-%d'),
            'price': 1500.0,
            'seats_max': 1,
        }])

@odoo.tests.tagged('post_install', '-at_install')
class TestUi(TestPosEventHttpCommon):
    def test_01_pos_event_tour(self):
        pass
    #     # open a session, the /pos/ui controller will redirect to it
    #     self.main_pos_config.with_user(self.pos_user).open_ui()
    #     self.start_tour(
    #         "/pos/ui?config_id=%d" % self.main_pos_config.id,
    #         "PosEventTour",
    #         login="pos_user",
    #         watch=True
    #     )
    #     event_id = self.env['event.event'].search([('name', '=', 'Conference for Architects TEST')])
    #     event_ticket = self.env['event.event.ticket'].search([('name', '=', 'Standard'), ('event_id', '=', event_id.id)])
    #     self.assertEqual(event_ticket.seats_available, 95)
    #     registration_count = self.env['event.registration'].search_count([('name', '=', 'A simple PoS man!')])
    #     self.assertEqual(registration_count, 5)

    # def test_02_partner_mandatory(self):
    #     self.main_pos_config.with_user(self.pos_user).open_ui()
    #     self.start_tour(
    #         "/pos/ui?config_id=%d" % self.main_pos_config.id,
    #         "PartnerMandatory",
    #         login="pos_user",
    #     )

    # def test_03_soldout_ticket(self):
    #     self.main_pos_config.with_user(self.pos_user).open_ui()
    #     self.start_tour(
    #         "/pos/ui?config_id=%d" % self.main_pos_config.id,
    #         "SoldoutTicket",
    #         login="pos_user",
    #     )
