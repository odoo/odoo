# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSyncing(CommonPosTest):

    def test_flush(self):
        products = [self.ten_dollars_no_tax.product_variant_id, self.twenty_dollars_no_tax.product_variant_id]
        id_updates = self.pos_config_usd.sudo().flush(
            [
                [
                    "CREATE",
                    "pos.order",
                    {
                        "pos_reference": "1stOrder",
                        "lines": [],
                        "uuid": "73f1e692-4459-415c-92c2-546ed3e6cf7c",
                        "_frontend_field": """fields starting with underscore are only for the frontend and `flush` should ignore them.
                        The reason that we still send them to the backend is that we want the backend to propagate the changes to the other clients.""",
                    },
                ],
                [
                    "CREATE",
                    "pos.order.line",
                    {
                        "qty": 1,
                        "product_id": products[0].id,
                        "uuid": "b0f3b23e-b08a-40a4-840d-5271ac5d1126",
                        "order_id": "73f1e692-4459-415c-92c2-546ed3e6cf7c",
                    },
                ],
                [
                    "CREATE",
                    "pos.order.line",
                    {
                        "qty": 2,
                        "product_id": products[1].id,
                        "uuid": "dccb0824-692a-449e-88a4-554815327f73",
                        "order_id": "73f1e692-4459-415c-92c2-546ed3e6cf7c",
                    },
                ],
            ],
            login_number=1
        )
        order = self.env['pos.order'].sudo().search([('pos_reference', '=', '1stOrder')])
        expected_id_updates = {
            "73f1e692-4459-415c-92c2-546ed3e6cf7c": order.id,
            "b0f3b23e-b08a-40a4-840d-5271ac5d1126": self.env['pos.order.line'].sudo().search([('uuid', '=', 'b0f3b23e-b08a-40a4-840d-5271ac5d1126')]).id,
            "dccb0824-692a-449e-88a4-554815327f73": self.env['pos.order.line'].sudo().search([('uuid', '=', 'dccb0824-692a-449e-88a4-554815327f73')]).id,
        }
        self.assertEqual(json.dumps(id_updates), json.dumps(expected_id_updates))

        self.assertEqual(order.pos_reference, "1stOrder")
        self.assertEqual(order.uuid, "73f1e692-4459-415c-92c2-546ed3e6cf7c")
        self.assertEqual(order.lines.mapped('qty'), [1, 2])
        self.assertEqual(order.lines.mapped('product_id.id'), [products[0].id, products[1].id])
        self.assertEqual(order.lines.mapped('uuid'), ["b0f3b23e-b08a-40a4-840d-5271ac5d1126", "dccb0824-692a-449e-88a4-554815327f73"])
