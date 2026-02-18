# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.addons.l10n_vn_edi_viettel.tests.test_edi import TestVNEDI
from odoo.tests import tagged
from odoo import Command


@tagged("post_install_l10n", "post_install", "-at_install")
class TestVNEDIPOS(TestVNEDI, TestPointOfSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.template_2 = cls.env['l10n_vn_edi_viettel.sinvoice.template'].create({
            'name': '2/0024',
            'template_invoice_type': '2',
        })
        cls.symbol_2 = cls.env['l10n_vn_edi_viettel.sinvoice.symbol'].create({
            'name': 'C25MNK',
            'invoice_template_id': cls.template_2.id,
        })
        cls.company.write({
            "l10n_vn_pos_default_symbol": cls.symbol.id,
        })
        cls.walk_in_customer = cls.env.ref('l10n_vn_edi_viettel_pos.partner_walk_in_customer')

        cls.pos_config.open_ui()
        cls.session = cls.pos_config.current_session_id

    def _create_simple_order(self):
        return self.PosOrder.create(
            {
                "name": "Order/0001",
                "session_id": self.session.id,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product.product_variant_id.id,
                            "qty": 3,
                            "price_unit": 1.0,
                            "price_subtotal": 3.0,
                            "price_subtotal_incl": 3.0,
                        }
                    )
                ],
                "partner_id": self.walk_in_customer.id,
                "amount_tax": 0.0,
                "amount_total": 3.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
            }
        )

    def test_default_symbol(self):
        """Test default symbol on POS order invoice."""
        pos_order = self._create_simple_order()
        invoice_vals = pos_order._prepare_invoice_vals()
        self.assertEqual(
            invoice_vals["l10n_vn_edi_invoice_symbol"],
            self.symbol.id,
            "The invoice symbol on the invoice values should be the default symbol of the company.",
        )

    def test_pos_specific_symbol(self):
        """Test POS specific symbol on POS order invoice."""
        self.pos_config.l10n_vn_pos_symbol = self.symbol_2.id
        pos_order = self._create_simple_order()
        invoice_vals = pos_order._prepare_invoice_vals()
        self.assertEqual(
            invoice_vals["l10n_vn_edi_invoice_symbol"],
            self.symbol_2.id,
            "The invoice symbol on the invoice values should be the symbol set in the POS configuration.",
        )

    @freeze_time('2024-01-01')
    def test_invoice_send_and_print(self):
        """ Test the invoice creation, sending and printing from a POS order."""
        order = self._create_simple_order()
        move_vals = order._prepare_invoice_vals()
        invoice = order._create_invoice(move_vals)
        invoice.action_post()

        self.assertEqual(invoice.l10n_vn_edi_invoice_state, 'ready_to_send')
        self._send_invoice(invoice)

        self.assertRecordValues(
            invoice,
            [{
                'l10n_vn_edi_invoice_number': 'K24TUT01',
                'l10n_vn_edi_reservation_code': '123456',
                'l10n_vn_edi_invoice_state': 'sent',
            }]
        )
        self.assertNotEqual(invoice.l10n_vn_edi_sinvoice_xml_file, False)
        self.assertNotEqual(invoice.l10n_vn_edi_sinvoice_pdf_file, False)
        self.assertNotEqual(invoice.l10n_vn_edi_sinvoice_file, False)

    @freeze_time('2024-01-01')
    def test_invoice_refund(self):
        """ Test the refund flow of PoS order"""
        order = self._create_simple_order()
        move_vals = order._prepare_invoice_vals()
        invoice = order._create_invoice(move_vals)
        invoice.action_post()
        self._send_invoice(invoice)

        refund_order = order._refund()
        refund_move_vals = refund_order._prepare_invoice_vals()
        refund_invoice = refund_order._create_invoice(refund_move_vals)
        refund_invoice.action_post()

        self.assertEqual(refund_invoice.l10n_vn_edi_invoice_state, 'ready_to_send')
        self._send_invoice(refund_invoice)
        self.assertRecordValues(
            refund_invoice,
            [{
                'l10n_vn_edi_invoice_number': 'K24TUT01',
                'l10n_vn_edi_reservation_code': '123456',
                'l10n_vn_edi_invoice_state': 'sent',
            }]
        )
        self.assertNotEqual(refund_invoice.l10n_vn_edi_sinvoice_xml_file, False)
        self.assertNotEqual(refund_invoice.l10n_vn_edi_sinvoice_pdf_file, False)
        self.assertNotEqual(refund_invoice.l10n_vn_edi_sinvoice_file, False)
