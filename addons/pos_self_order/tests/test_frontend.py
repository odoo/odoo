# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo import Command


@odoo.tests.tagged("post_install", "-at_install")
class TestFrontendMobile(SelfOrderCommonTest):
    def test_order_fiscal_position(self):
        """ Orders made in take away should have the alternative fiscal position. """

        tax30 = self.env['account.tax'].create({
            'name': '30%',
            'amount': 30,
            'amount_type': 'percent',
        })

        alternative_fp = self.env['account.fiscal.position'].create({
            'name': "Test",
            'auto_apply': True,
            'tax_ids': [
                Command.create({
                    'tax_src_id': self.default_tax15.id,
                    'tax_dest_id': tax30.id,
                }),
            ]
        })

        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_takeaway': True,
            'self_ordering_alternative_fp_id': alternative_fp.id,
        })

        self.pos_config.open_ui()

        response = self.url_open(
            "/pos-self-order/process-new-order/kiosk",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "id": str(uuid4()),
                "params": {
                    "access_token": self.pos_config.access_token,
                    "order": {
                        "id": None,
                        "pos_config_id": self.pos_config.id,
                        "access_token": None,
                        "pos_reference": None,
                        "state": "draft",
                        "date": None,
                        "amount_total": 0,
                        "amount_tax": 0,
                        "lines": [],
                        "tracking_number": None,
                        "take_away": True,
                        "lastChangesSent": {},
                    },
                    "table_identifier": None,
                }
            }),
            headers={"Content-Type": "application/json"},
        )

        result = response.json()
        order_id = result['result']['id']
        self.assertEqual(self.env['pos.order'].browse(order_id).fiscal_position_id.id, alternative_fp.id)

    def test_properly_delete_splash_screen_images(self):
        """ Simulate what is done from the res.config.settings view when removing an image. """

        self.pos_config.write({
            'self_ordering_image_home_ids': [
                Command.clear(),
                Command.create({'name': 'a1', 'datas': b'blob1234', 'mimetype': 'image/png'}),
                Command.create({'name': 'a2', 'datas': b'blob2345', 'mimetype': 'image/png'}),
                Command.create({'name': 'a3', 'datas': b'blob3456', 'mimetype': 'image/png'}),
            ]
        })

        linked_ids = self.pos_config.self_ordering_image_home_ids.ids
        second_id = linked_ids[1]

        # We'll unlink the second image and then save the settings.
        # It will be a set of link commands for the images except the one we want to delete.
        commands = [Command.link(id) for id in linked_ids if id != second_id]
        self.pos_config.with_context(from_settings_view=True).write({
            'self_ordering_image_home_ids': commands
        })

        self.assertTrue(second_id not in self.pos_config.self_ordering_image_home_ids.ids)
