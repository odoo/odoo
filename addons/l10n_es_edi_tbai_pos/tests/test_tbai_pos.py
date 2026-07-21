from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.l10n_es_edi_tbai.tests.common import TestEsEdiTbaiCommonGipuzkoa
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import NS_MAP
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosEdi(TestEsEdiTbaiCommonGipuzkoa, TestPointOfSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_es = cls.env['res.partner'].create({
            'name': 'ES Partner',
            'vat': 'ESF35999705',
            'country_id': cls.env.ref('base.es').id,
            'invoice_edi_format': None,
        })

    @classmethod
    def create_pos_order(cls, session, price_unit):
        return cls.PosOrder.create({
            'session_id': session.id,
            'lines': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'price_unit': price_unit,
                    'qty': 1,
                    'tax_ids': cls._get_tax_by_xml_id('s_iva21b').ids,
                    'price_subtotal': price_unit,
                    'price_subtotal_incl': price_unit * 1.21,
                }),
            ],
            'amount_tax': 0.21 * price_unit,
            'amount_total': 1.21 * price_unit,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

    @classmethod
    def pay_pos_order(cls, pos_order, with_error=False):
        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = cls.PosMakePayment.with_context(context_make_payment).create({
            'amount': pos_order.amount_total,
        })
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=None if with_error else cls.mock_response_post_invoice_success,
            side_effect=cls.mock_request_error if with_error else None,
        ):
            pos_make_payment.with_context(context_make_payment).check()

    def test_tbai_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        pos_order = self.create_pos_order(current_session, 100.0)
        self.pay_pos_order(pos_order)

        self.assertEqual(pos_order.state, 'paid')
        self.assertEqual(pos_order.l10n_es_tbai_state, 'sent')

    def test_tbai_pos_order_to_invoice(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        pos_order = self.create_pos_order(current_session, 500.0)

        # The amount is above 400 (default simplified invoice limit) so an error should be raised if it's not invoiced
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_order)

        # Now with the pos order invoiced
        pos_order.partner_id = self.partner_es
        pos_order.to_invoice = True
        self.pay_pos_order(pos_order)

        self.assertEqual(pos_order.state, 'invoiced')
        # The edi is handled by the invoice
        self.assertFalse(pos_order.l10n_es_tbai_state)

    def test_tbai_refund_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # Create and pay a pos order not invoiced
        pos_order = self.create_pos_order(current_session, 100.0)
        self.pay_pos_order(pos_order)

        # Create the refund
        refund_action = pos_order.refund()
        pos_refund = self.PosOrder.browse(refund_action['res_id'])

        # An error is raised if the refund is invoiced
        pos_refund.to_invoice = True
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_refund)

        # Now works with the refund not invoiced
        pos_refund.to_invoice = False
        self.pay_pos_order(pos_refund)

        self.assertEqual(pos_refund.state, 'paid')
        self.assertEqual(pos_refund.l10n_es_tbai_state, 'sent')

    def test_tbai_refund_invoiced_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # Create and pay a pos order not invoiced
        pos_order = self.create_pos_order(current_session, 500.0)
        pos_order.partner_id = self.partner_es
        pos_order.to_invoice = True
        self.pay_pos_order(pos_order)

        # Create the refund
        refund_action = pos_order.refund()
        pos_refund = self.PosOrder.browse(refund_action['res_id'])

        # An error is raised if the refund is not invoiced
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_refund)

        # Now works with the refund invoiced
        pos_refund.to_invoice = True
        self.pay_pos_order(pos_refund)

        self.assertEqual(pos_refund.state, 'invoiced')
        self.assertFalse(pos_refund.l10n_es_tbai_state)

    def test_tbai_pos_order_with_failed_chain_head(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        pos_order = self.create_pos_order(current_session, 100.0)
        self.pay_pos_order(pos_order, with_error=True)

        self.assertNotEqual(pos_order.l10n_es_tbai_state, 'sent')

        pos_order2 = self.create_pos_order(current_session, 101.0)
        self.pay_pos_order(pos_order2)

        # the second order should retry the unposted chain head
        self.assertEqual(pos_order.l10n_es_tbai_state, 'sent')
        self.assertEqual(pos_order2.l10n_es_tbai_state, 'sent')

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

        self.pos_config.module_pos_discount = True
        discount_product = self.env.ref("pos_discount.product_product_consumable", raise_if_not_found=False)
        self.pos_config.discount_product_id = discount_product

        self.pos_config.open_ui()
        product_price, discount = 100, -10
        pos_order = {
            "amount_tax": 0.21 * (product_price + discount),
            "amount_total": 1.21 * (product_price + discount),
            "amount_paid": 0.0,
            "amount_return": 0.0,
            "session_id": self.pos_config.current_session_id.id,
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
                        "payment_method_id": self.pos_config.payment_method_ids[0].id,
                }),
            ],
            "uuid": "00044-003-0014",
        }
        results = self.PosOrder.sync_from_ui([pos_order])
        pos_order = self.PosOrder.browse(results['pos.order'][0]['id'])

        refund_action = pos_order.refund()
        pos_refund = self.PosOrder.browse(refund_action['res_id'])

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
