# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import odoo.tests
from odoo.tests.common import HttpCase


@odoo.tests.tagged('post_install', '-at_install')
class TestFrontDeskURL(HttpCase):
    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------
    def test_frontdesk_ui(self):
        '''Testing the UI of the Frontdesk module'''
        station = self.env['frontdesk.frontdesk'].create({
            'name': 'Test Office 1',
            'responsible_ids': [(4, self.env.ref('base.user_admin').id)],
            'self_check_in': True,
            'drink_offer': True,
            'drink_ids': [(4, self.env.ref(f'frontdesk.frontdesk_drink_{i}').id) for i in [1, 2]],
        })
        self.env["frontdesk.visitor"].create({
            'name': 'Tony Stark',
            'phone': '1230004567',
            'email': 'stark@industries.com',
            'check_in': datetime.now(),
            'state': 'planned',
            'station_id': station.id,
        })
        self.env.ref('base.user_admin').name = 'Mitchell Admin'
        kiosk_values = station.action_open_kiosk()
        access_url = kiosk_values.get('url')

        self.start_tour(access_url, 'quick_check_in_tour', login='admin', step_delay=100)
        station.drink_offer = True
        self.start_tour(access_url, 'frontdesk_basic_tour', login='admin', step_delay=100)
        station.write({
            'host_selection': True,
            'ask_email': 'required',
        })
        self.start_tour(access_url, 'required_fields_tour', login='admin', step_delay=100)
