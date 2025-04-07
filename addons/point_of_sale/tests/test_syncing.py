# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSyncing(TestPoSCommon):

    def test_flush(self):

        # cls = self
        # cls.pos_user = cls.env['res.users'].create({
        #     'name': 'A simple PoS man!',
        #     'login': 'pos_user',
        #     'password': 'pos_user',
        #     'group_ids': [
        #         (4, cls.env.ref('base.group_user').id),
        #         (4, cls.env.ref('point_of_sale.group_pos_user').id),
        #         (4, cls.env.ref('stock.group_stock_user').id),
        #     ],
        #     'tz': 'America/New_York',
        # })
        # self.env = self.env(user=self.pos_user)
        # id_updates = self.env(user=self.pos_user)['pos.config'].search([])[0].flush(
        # self.env.user
        # self.config = self.basic_config
        self.pos_user = self.env['res.users'].create({
            'name': 'A simple PoS man!',
            'login': 'pos_user',
            'password': 'pos_user',
            'group_ids': [
                (4, self.env.ref('base.group_user').id),
                (4, self.env.ref('point_of_sale.group_pos_user').id),
                (4, self.env.ref('stock.group_stock_user').id),
            ],
            'tz': 'America/New_York',
        })
        # self.open_new_session()
        login_number = 1
        id_updates = self.basic_config.with_user(self.pos_user).flush(
            [
                [
                    "CREATE",
                    "pos.order",
                    {
                        "pos_reference": "1stOrder",
                        "lines": [],
                        "uuid": "73f1e692-4459-415c-92c2-546ed3e6cf7c",
                    },
                ],
                [
                    "CREATE",
                    "pos.order.line",
                    {
                        "qty": 1,
                        "product_id": 1,
                        "uuid": "b0f3b23e-b08a-40a4-840d-5271ac5d1126",
                        "order_id": "73f1e692-4459-415c-92c2-546ed3e6cf7c",
                    },
                ],
                [
                    "CREATE",
                    "pos.order.line",
                    {
                        "qty": 2,
                        "product_id": 2,
                        "uuid": "dccb0824-692a-449e-88a4-554815327f73",
                        "order_id": "73f1e692-4459-415c-92c2-546ed3e6cf7c",
                    },
                ],
            ],
            login_number
        )
        expected_id_updates = {
            "73f1e692-4459-415c-92c2-546ed3e6cf7c": 1,
            "b0f3b23e-b08a-40a4-840d-5271ac5d1126": 1,
            "dccb0824-692a-449e-88a4-554815327f73": 2,
        }
        self.assertEqual(json.dumps(id_updates), json.dumps(expected_id_updates))

        order = self.env['pos.order'].browse(1)
        self.assertEqual(order.pos_reference, "1stOrder")
        self.assertEqual(order.uuid, "73f1e692-4459-415c-92c2-546ed3e6cf7c")
        self.assertEqual(order.lines.mapped('qty'), [1, 2])
        self.assertEqual(order.lines.mapped('product_id.id'), [1, 2])
        self.assertEqual(order.lines.mapped('uuid'), ["b0f3b23e-b08a-40a4-840d-5271ac5d1126", "dccb0824-692a-449e-88a4-554815327f73"])
