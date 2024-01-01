# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWEventBoothExhibitorCommon(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def test_register(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.env.ref('base.user_admin').write({
            'name': 'Mitchell Admin',
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
        })

        self.env['event.event'].create({
            'name': 'Test Online Reveal',
            'date_tz': 'Europe/Brussels',
            'stage_id': self.env.ref('event.event_stage_booked').id,
            'date_begin': datetime.now() + relativedelta(days=1, hour=5, minute=0, second=0),
            'date_end': datetime.now() + relativedelta(days=1, hour=5, minute=0, second=0),
            'auto_confirm': True,
            'is_published': True,
            'website_menu': True,
            'booth_menu': True,
            'exhibitor_menu': True,
            'event_booth_ids': [(0, 0, {
                'name': 'Standard Booth',
                'booth_category_id': self.env.ref('event_booth.event_booth_category_standard').id,
            }), (0, 0, {
                'name': 'OpenWood Demonstrator 2',
                'booth_category_id': self.env.ref('event_booth.event_booth_category_premium').id,
            })]
        })
        self.browser_js(
            '/event',
            'odoo.__DEBUG__.services["web_tour.tour"].run("webooth_exhibitor_register")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.webooth_exhibitor_register.ready',
            login='admin'
        )
