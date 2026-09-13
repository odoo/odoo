# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from datetime import timedelta
from unittest.mock import patch
from freezegun import freeze_time

import odoo.tests
from odoo.exceptions import UserError
from odoo import Command, http, fields
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_self_order.models.pos_self_order_kiosk_pairing_request import (
    MAX_PENDING_REQUESTS_PER_IP_PARAM,
)


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderKiosk(SelfOrderCommonTest):
    def test_self_order_kiosk(self):
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        tax_10_inc = self.env['account.tax'].create({
            "name": "10% incl",
            "amount": 10,
            "amount_type": "percent",
            "type_tax_use": "sale",
            "price_include_override": "tax_included",
            "include_base_amount": True,
        })

        tax_10_excl = self.env['account.tax'].create({
            "name": "10% excl",
            "amount": 10,
            "amount_type": "percent",
            "type_tax_use": "sale",
        })

        self.env['product.product'].create({
            'name': 'Yummy Burger',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': [Command.set([tax_10_inc.id])],
        })

        self.env['product.product'].create({
            'name': 'Taxi Burger',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': [Command.set([tax_10_inc.id, tax_10_excl.id])],
        })

        self.pos_config.write({
            'available_preset_ids': [(5, 0)],
        })

        # Without location choices, since we need preset to do so.
        order = self.process_self_order(
            [
                {
                    'product': self.cola,
                    'qty': 1,
                    'price_unit': self.cola.lst_price,
                },
            ],
            table_stand_number=3,
        )
        self.assertEqual("Table tracker 3", order.floating_order_name)

    def test_duplicate_order_kiosk(self):
        self.pos_config.write({
            'use_presets': False,
            'default_preset_id': False,
            'available_preset_ids': [(5, 0)],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_duplicate_order_kiosk")
        orders = self.env['pos.order'].search(['&', ('state', '=', 'draft'), '|', ('config_id', '=', self.pos_config.id), ('config_id', 'in', self.pos_config.trusted_config_ids.ids)])
        self.assertEqual(len(orders), 1)

    def test_self_order_language_changes(self):
        self.env['res.lang']._activate_lang('fr_FR')

        test_category = self.env['pos.category'].create({
            'name': "Test Category",
        })

        product = self.env['product.product'].create({
            'name': "Test Product",
            'list_price': 100,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, test_category.id)],
        })
        test_category.with_context(lang='fr_FR').name = "Catégorie Test"
        product.with_context(lang='fr_FR').name = "Produit Test"

        self.pos_config.write({
            'self_ordering_available_language_ids': [Command.link(lang.id) for lang in self.env['res.lang'].search([])],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each'
        })
        link = self.env['pos_self_order.custom_link'].search(
            [('pos_config_ids', '=', self.pos_config.id), ('name', '=', 'Order Now')]
        )
        link.with_context(lang='fr_FR').name = "Commander maintenant"

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, 'self_order_language_changes')

    def test_self_order_kiosk_to_cashier_payment(self):
        self.pos_config.write({
            'use_presets': False,
            'default_preset_id': False,
            'available_preset_ids': [Command.clear()],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'use_pricelist': True,
        })
        cashier_pos = self.env['pos.config'].create({
            'name': 'Shop',
            'module_pos_restaurant': False,
            'cash_control': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.process_self_order(
            [
                {
                    'product': self.cola,
                    'qty': 1,
                    'price_unit': self.cola.lst_price,
                },
            ],
        )
        self.start_tour(f"/pos/ui/{cashier_pos.id}", 'test_pay_unpaid_order_from_kiosk', login="admin")

    def test_self_order_kiosk_ordering_images_public(self):
        def assert_all_image_public():
            self.assertTrue(all(img.public for img in self.pos_config.self_ordering_image_home_ids))
            self.assertTrue(all(img.public for img in self.pos_config.self_ordering_image_background_ids))

        def create_fake_attachment():
            return self.env["ir.attachment"].create(
                {
                    "name": f"test_{random.randint(1000, 9999)}",
                    "raw": b"test",
                },
            )

        assert_all_image_public()

        for field in ["self_ordering_image_home_ids", "self_ordering_image_background_ids"]:
            # SET
            new_att = create_fake_attachment()
            self.pos_config.write({field: [Command.set([new_att.id])]})
            self.assertEqual(len(self.pos_config[field]), 1)
            assert_all_image_public()

            # LINK
            new_att = create_fake_attachment()
            self.pos_config.write({field: [Command.link(new_att.id)]})
            self.assertEqual(len(self.pos_config[field]), 2)
            assert_all_image_public()

            # CREATE
            self.pos_config.write(
                {
                    field: [
                        Command.create(
                            {
                                "name": f"test_{field}",
                                "raw": b"test",
                            },
                        ),
                    ],
                },
            )
            self.assertEqual(len(self.pos_config[field]), 3)
            assert_all_image_public()

    def test_self_order_kiosk_ordering_images_clear(self):
        self.assertEqual(len(self.pos_config.self_ordering_image_home_ids), 3)
        self.assertEqual(len(self.pos_config.self_ordering_image_background_ids), 1)

        self.pos_config.write(
            {
                "self_ordering_image_home_ids": [Command.clear()],
                "self_ordering_image_background_ids": [Command.clear()],
            }
        )
        self.pos_config.write(
            {
                "self_ordering_mode": "kiosk",
                "self_ordering_image_home_ids": [],
                "self_ordering_image_background_ids": [],
            }
        )
        # Default home images are automatically assigned when all images are removed
        self.assertEqual(len(self.pos_config.self_ordering_image_home_ids), 3)
        # Background images can be fully cleared
        self.assertEqual(len(self.pos_config.self_ordering_image_background_ids), 0)

    def test_self_order_receipt_without_preset(self):
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'use_presets': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        order = self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'amount_paid': 0.0,
            'source': 'mobile',
            'lines': [(0, 0, {
                'qty': 1,
                'product_id': self.cola.id,
                'price_unit': self.cola.lst_price,
                'price_subtotal': self.cola.lst_price,
                'price_subtotal_incl': self.cola.lst_price,
            })],
        })
        html = order.order_receipt_generate_html()
        self.assertTrue("Service at Table" in html)

    def test_pairing_tour(self):
        """The kiosk pairing screen shows a code and redirects to the kiosk once it is validated."""
        self.pos_config.write({'self_ordering_mode': 'kiosk'})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')
        self_route = self.pos_config._get_self_order_route()
        user_admin = self.pos_admin

        @http.route('/pos-self-order/test-approve-pairing', auth='public', type='jsonrpc')
        def approve_pairing(self, config_id):
            config = self.env['pos.config'].sudo().browse(int(config_id)).exists()
            pairing_request = self.env['pos_self_order.kiosk.pairing.request'].sudo().search(
                [('config_id', '=', config.id), ('approved', '=', False)], limit=1,
            )
            self.env['pos_self_order.kiosk.device'].with_user(user_admin)._create_from_pairing(pairing_request)

        with patch.object(PosSelfOrderController, 'approve_pairing', approve_pairing, create=True):
            super(SelfOrderCommonTest, self).start_tour(self_route, 'pos_self_order_pairing_tour')

        pairing_requests = self.env['pos_self_order.kiosk.pairing.request'].search([
            ('config_id', '=', self.pos_config.id),
        ])
        self.assertTrue(pairing_requests)
        approved = pairing_requests.filtered('approved')
        self.assertTrue(approved)
        self.assertTrue(approved.device_id)

    def test_pairing_throttled_tour(self):
        self.pos_config.write({'self_ordering_mode': 'kiosk'})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        PairingRequest = self.env['pos_self_order.kiosk.pairing.request']
        self.env['ir.config_parameter'].sudo().set_int(MAX_PENDING_REQUESTS_PER_IP_PARAM, 3)

        for i in range(3):
            PairingRequest._create_request(self.pos_config, "127.0.0.1", "ua_" + str(i))

        failed_error = False
        try:
            PairingRequest._create_request(self.pos_config, '127.0.0.1', 'uaxxxx')
        except UserError as error:
            failed_error = error

        self.assertIn("Too many pending pairing requests", str(failed_error))

        # Other IP should be able to create a request
        PairingRequest._create_request(self.pos_config, '127.0.0.2', 'uaxxxx')

        # cleanup expired requests and try again
        with freeze_time(fields.Datetime.now() + timedelta(minutes=20)):
            PairingRequest._cron_cleanup_expired()

        PairingRequest._create_request(self.pos_config, '127.0.0.1', 'uaxxxx')
