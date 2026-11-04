# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from unittest.mock import patch

import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest

CHANGE_RECEIPT_ROUTE = '/pos-self-order/kiosk/change-receipt'


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderReceiptLang(SelfOrderCommonTest):
    def _setup_change_receipt_order(self):
        """Create a paid kiosk order on a config with a receipt and a label preparation printer."""
        self.env['res.lang']._activate_lang('fr_FR')
        self.cola.with_context(lang='fr_FR').name = 'Coca-Cola FR'
        categories = self.cola.pos_categ_ids
        receipt_printer = self.env['pos.printer'].create({
            'name': 'Kitchen Printer',
            'printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'product_categories_ids': categories.ids,
        })
        label_printer = self.env['pos.printer'].create({
            'name': 'Label Printer',
            'printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'paper_size': 'label',
            'product_categories_ids': categories.ids,
        })
        small_printer = self.env['pos.printer'].create({
            'name': 'Small Printer',
            'printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'paper_size': '58',
            'product_categories_ids': categories.ids,
        })
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'preparation_printer_ids': [receipt_printer.id, label_printer.id, small_printer.id],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        order_data = self._create_order_data(
            state='draft',
            product=self.cola,
            qty=3,
            price_unit=2.2,
            price_subtotal_incl=6.6,
            payments=[[0, 0, {'payment_method_id': self.bank_payment_method.id, 'amount': 6.6}]],
        )
        data = self.make_request_to_controller('/pos-self-order/process-order/kiosk', order_data)
        order = self.env['pos.order'].browse(data['pos.order'][0]['id'])
        return order, receipt_printer, label_printer

    def _request_change_receipt(self, order, access_token):
        """Call the change receipt endpoint, rendering each HTML body as the "image" bytes."""
        def fake_run_image_engine(report, engine_name, bodies, width, height, image_format='jpg'):
            return [str(body).encode() for body in bodies]

        with patch.object(self.env.registry['ir.actions.report'], '_run_image_engine', fake_run_image_engine):
            return self.make_request_to_controller(
                f'{CHANGE_RECEIPT_ROUTE}/{order.id}',
                {'access_token': self.pos_config.access_token, 'order_access_token': access_token},
            )

    def test_change_receipt_rendered_in_default_user_lang(self):
        order, receipt_printer, label_printer = self._setup_change_receipt_order()

        for lang, expected, unexpected in (
            ('fr_FR', 'Coca-Cola FR', None),
            ('en_US', 'Coca-Cola', 'Coca-Cola FR'),
        ):
            with self.subTest(lang=lang):
                self.pos_user.lang = lang
                data = self._request_change_receipt(order, order.access_token)

                # The server only renders 80mm printers, the frontend prints the others
                self.assertEqual(list(data['receipts']), [str(receipt_printer.id)])
                self.assertNotIn(str(label_printer.id), data['receipts'])

                # The whole order is rendered, even if it was already sent to preparation
                images = data['receipts'][str(receipt_printer.id)]
                self.assertEqual(len(images), 1)
                html = base64.b64decode(images[0]).decode()
                self.assertIn(expected, html)
                if unexpected:
                    self.assertNotIn(unexpected, html)

    def test_change_receipt_skips_printers_of_other_categories(self):
        order, receipt_printer, _label_printer = self._setup_change_receipt_order()
        receipt_printer.product_categories_ids = self.env['pos.category'].create({'name': 'Unmatched'})

        data = self._request_change_receipt(order, order.access_token)

        self.assertNotIn(str(receipt_printer.id), data['receipts'])

    def test_change_receipt_without_receipt_printer(self):
        order, _receipt_printer, label_printer = self._setup_change_receipt_order()
        self.pos_config.preparation_printer_ids = label_printer

        data = self._request_change_receipt(order, order.access_token)

        self.assertEqual(data['receipts'], {})

    def test_change_receipt_requires_valid_access_token(self):
        order, _receipt_printer, _label_printer = self._setup_change_receipt_order()

        for access_token in (None, 'wrong-token', self.pos_config.access_token):
            with self.subTest(access_token=access_token):
                data = self._request_change_receipt(order, access_token)
                self.assertIsNone(data)

    def test_change_receipt_requires_config_access_token(self):
        order, _receipt_printer, _label_printer = self._setup_change_receipt_order()

        data = self.make_request_to_controller(
            f'{CHANGE_RECEIPT_ROUTE}/{order.id}',
            {'access_token': 'wrong-token', 'order_access_token': order.access_token},
        )
        self.assertIsNone(data)

    def test_change_receipt_only_returns_the_receipt_printer_with_a_label_printer(self):
        order, receipt_printer, label_printer = self._setup_change_receipt_order()
        self.pos_config.preparation_printer_ids = receipt_printer | label_printer

        data = self._request_change_receipt(order, order.access_token)

        self.assertEqual(list(data['receipts']), [str(receipt_printer.id)])
        self.assertEqual(len(data['receipts'][str(receipt_printer.id)]), 1)

    def test_change_receipt_returns_no_image_when_one_failed_to_render(self):
        order, receipt_printer, _label_printer = self._setup_change_receipt_order()

        def fake_run_image_engine(report, engine_name, bodies, width, height, image_format='jpg'):
            return [b'image', None]

        with patch.object(self.env.registry['ir.actions.report'], '_run_image_engine', fake_run_image_engine):
            data = self.make_request_to_controller(
                f'{CHANGE_RECEIPT_ROUTE}/{order.id}',
                {'access_token': self.pos_config.access_token, 'order_access_token': order.access_token},
            )

        self.assertEqual(data['receipts'][str(receipt_printer.id)], [])

    def test_change_receipt_is_kiosk_only(self):
        order, _receipt_printer, _label_printer = self._setup_change_receipt_order()
        self.pos_config.self_ordering_mode = 'mobile'

        self.assertIsNone(self._request_change_receipt(order, order.access_token))
