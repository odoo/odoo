from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.l10n_es_edi_tbai.tests.common import TestEsEdiTbaiCommonGipuzkoa
from odoo.addons.l10n_es_edi_tbai_pos.tests.common import CommonPosEsEdiTest
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import NS_MAP
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosEdi(TestEsEdiTbaiCommonGipuzkoa, CommonPosEsEdiTest):
    @classmethod
    def pay_pos_order(self, pos_order, with_error=False):
        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'amount': pos_order.amount_total,
        })
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=None if with_error else self.mock_response_post_invoice_success,
            side_effect=self.mock_request_error if with_error else None,
        ):
            pos_make_payment.with_context(context_make_payment).check()

    def test_tbai_pos_order(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 100
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.l10n_es_tbai_state, 'sent')

    def test_tbai_pos_order_to_invoice(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 500
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })

        # The amount is above 400 (default simplified invoice limit) so an error should be raised if it's not invoiced
        with self.assertRaises(UserError):
            self.pay_pos_order(order)

        order.partner_id = self.partner_lowe
        order.to_invoice = True
        self.pay_pos_order(order)

        self.assertTrue(order.account_move)
        # The edi is handled by the invoice
        self.assertFalse(order.l10n_es_tbai_state)

    def test_tbai_refund_pos_order(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 100
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order)

        # Create the refund
        refund_action = order.refund()
        pos_refund = self.env['pos.order'].browse(refund_action['res_id'])

        # An error is raised if the refund is invoiced
        pos_refund.to_invoice = True
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_refund)

        # Now works with the refund not invoiced
        pos_refund.to_invoice = False
        self.pay_pos_order(pos_refund)

        self.assertEqual(pos_refund.state, 'paid')
        self.assertEqual(pos_refund.l10n_es_tbai_state, 'sent')

        orig_num = order.l10n_es_tbai_post_document_id._get_tbai_sequence_and_number()[1]
        refund_num = pos_refund.l10n_es_tbai_post_document_id._get_tbai_sequence_and_number()[1]
        self.assertNotEqual(orig_num, refund_num)

    def test_tbai_refund_invoiced_pos_order(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 100
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_lowe.id,
                'to_invoice': True,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order)
        refund_action = order.refund()
        pos_refund = self.env['pos.order'].browse(refund_action['res_id'])

        # An error is raised if the refund is not invoiced
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_refund)

        # Now works with the refund invoiced
        pos_refund.to_invoice = True
        self.pay_pos_order(pos_refund)
        self.assertTrue(pos_refund.account_move)
        self.assertFalse(pos_refund.l10n_es_tbai_state)

    def test_tbai_pos_order_with_failed_chain_head(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 100
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order, with_error=True)
        self.assertNotEqual(order.l10n_es_tbai_state, 'sent')

        order2, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order2)

        # the second order should retry the unposted chain head
        self.assertEqual(order.l10n_es_tbai_state, 'sent')
        self.assertEqual(order2.l10n_es_tbai_state, 'sent')

    def test_tbai_xml_order_and_refund_line_amounts_with_discount(self):
        if self.env['ir.module.module']._get('pos_discount').state != 'installed':
            self.skipTest("pos_discount module is required for this test")

        def get_edi_doc_in_xml(order):
            edi_document = order._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(order._l10n_es_tbai_get_values())
            xml_doc = edi_document._get_xml()
            xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
            return xml_doc

        def assert_order_line(line, cantidad, unitario, total):
            self.assertEqual(line.find("Cantidad").text, cantidad)
            self.assertEqual(line.find("ImporteUnitario").text, unitario)
            self.assertEqual(line.find("ImporteTotal").text, total)

        self.pos_config_usd.module_pos_discount = True
        discount_product = self.env.ref("pos_discount.product_product_consumable", raise_if_not_found=False)
        self.pos_config_usd.discount_product_id = discount_product

        self.pos_config_usd.open_ui()
        product_price, discount = 100, -10
        pos_order = {
            "amount_tax": 0.21 * (product_price + discount),
            "amount_total": 1.21 * (product_price + discount),
            "amount_paid": 0.0,
            "amount_return": 0.0,
            "session_id": self.pos_config_usd.current_session_id.id,
            "lines": [
                Command.create({
                        "product_id": self.product_a.id,
                        "price_unit": product_price,
                        "qty": 1,
                        "tax_ids": self._get_tax_by_xml_id("s_iva21b").ids,
                        "price_subtotal": product_price,
                        "price_subtotal_incl": product_price * 1.21,
                }),
                Command.create({
                        "product_id": discount_product.id,
                        "price_unit": discount,
                        "qty": 1,
                        "tax_ids": self._get_tax_by_xml_id("s_iva21b").ids,
                        "price_subtotal": discount,
                        "price_subtotal_incl": discount * 1.21,
                }),
            ],
            "payment_ids": [
                Command.create({
                        "amount": 1.21 * (product_price + discount),
                        "name": fields.Datetime.now(),
                        "payment_method_id": self.pos_config_usd.payment_method_ids[0].id,
                }),
            ],
            "uuid": "00044-003-0014",
        }
        results = self.env['pos.order'].sync_from_ui([pos_order])
        pos_order = self.env['pos.order'].browse(results['pos.order'][0]['id'])

        refund_action = pos_order.refund()
        pos_refund = self.env['pos.order'].browse(refund_action['res_id'])

        xml_doc = get_edi_doc_in_xml(pos_order)
        order_lines = xml_doc.find("Factura/DatosFactura/DetallesFactura")
        assert_order_line(order_lines[0], "1.00000000", "100.00000000", "121.00000000")
        assert_order_line(order_lines[1], "1.00000000", "-10.00000000", "-12.10000000")
        self.assertEqual(xml_doc.find("Factura/DatosFactura/ImporteTotalFactura").text, "108.90")

        xml_doc = get_edi_doc_in_xml(pos_refund)
        order_lines = xml_doc.find("Factura/DatosFactura/DetallesFactura")
        assert_order_line(order_lines[0], "1.00000000", "-100.00000000", "-121.00000000")
        assert_order_line(order_lines[1], "1.00000000", "10.00000000", "12.10000000")
        self.assertEqual(xml_doc.find("Factura/DatosFactura/ImporteTotalFactura").text, "-108.90")
