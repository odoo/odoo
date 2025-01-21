# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestFrontendMobile(SelfOrderCommonTest):
    def test_order_fiscal_position(self):
        """ Orders made in take away should have the alternative fiscal position. """

        alternative_fp = self.env['account.fiscal.position'].create({
            'name': "Test",
            'auto_apply': True,
        })
        self.env['account.tax'].create({
            'name': '30%',
            'amount': 30,
            'amount_type': 'percent',
            'fiscal_position_ids': alternative_fp,
        })

        self.out_preset.write({
            'fiscal_position_id': alternative_fp.id,
        })
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
        })

        self.pos_config.open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        response = self.url_open(
            "/pos-self-order/process-order/kiosk",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "id": str(uuid4()),
                "params": {
                    "access_token": self.pos_config.access_token,
                    "order": {
                        "id": None,
                        "config_id": self.pos_config.id,
                        "session_id": self.pos_config.current_session_id.id,
                        "access_token": None,
                        "pos_reference": None,
                        "state": "draft",
                        "preset_id": self.out_preset.id,
                        "amount_total": 0,
                        "amount_tax": 0,
                        "amount_paid": 0,
                        "amount_return": 0,
                        "lines": [],
                        "tracking_number": None,
                        "uuid": str(uuid4()),
                    },
                    "table_identifier": None,
                }
            }),
            headers={"Content-Type": "application/json"},
        )

        result = response.json()
        order_id = result['result']['pos.order'][0]['id']
        self.assertEqual(self.env['pos.order'].browse(order_id).fiscal_position_id.id, alternative_fp.id)
