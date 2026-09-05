from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr import CPRO_INVOICE_IDENTIFIER

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPdpXml(TestL10nFrPdpCommon):

    @classmethod
    def subfolders(cls):
        return 'ubl_21_fr', 'invoice', 'fr'

    def test_export_invoice_partner_fr(self):
        invoice = self._create_french_invoice()
        invoice.action_post()
        self._send_patched(invoice)
        self._assert_invoice_ubl_file(invoice, "ubl_21_fr_out_invoice")

    def test_export_invoice_partner_fr_without_pdp(self):
        """
        A French Peppol proxy user must have the BR-FR-05 mandatory notes
        (`PMT`, `PMD`, `AAB`) included in the `ubl_21_fr` exported XML.
        The export is tested directly rather than via send, as the patched
        send does not allow verifying the XML content in all versions.
        """
        self.env.company._reset_peppol_configuration()
        # To be able to generate the same XML as in `test_export_invoice_partner_fr`
        self.env.company.write({
            'peppol_eas': '0225',
            'peppol_endpoint': '968515759_96851575905899',
        })
        # Simulate a company that isn't connected to the PDP proxy at all
        self.proxy_user.unlink()

        invoice = self._create_french_invoice()
        invoice.action_post()

        wizard = self.create_send_and_print(invoice, sending_methods=['manual'], extra_edis=['ubl_21_fr'])
        wizard.action_send_and_print()
        self._assert_invoice_ubl_file(invoice, "ubl_21_fr_out_invoice")

    def test_export_credit_note_partner_fr(self):
        invoice = self._create_french_invoice()

        invoice.action_post()
        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((invoice.id,))],
                'date': self.fakenow.date(),
                'journal_id': invoice.journal_id.id,
            }
        ).reverse_moves()
        credit_note = invoice.reversal_move_ids
        credit_note.action_post()
        self._send_patched(credit_note)
        self._assert_invoice_ubl_file(credit_note, "ubl_21_fr_out_credit_note")

    def test_export_invoice_partner_fr_b2g(self):
        if self.env['ir.module.module']._get('l10n_fr_facturx_chorus_pro').state != 'installed':
            self.skipTest("'l10n_fr_facturx_chorus_pro' is not installed")

        self.partner_a.peppol_supported_documents = [CPRO_INVOICE_IDENTIFIER]
        self.assertTrue(self.env['account.edi.xml.ubl_21_fr']._pdp_is_b2g(self.partner_a))

        invoice = self._create_french_invoice(
            buyer_reference="Chorus Pro buyer reference",
            purchase_order_reference="Chorus Pro purchase order reference",
        )
        invoice.action_post()
        self._send_patched(invoice)
        self._assert_invoice_ubl_file(invoice, "ubl_21_fr_out_invoice_b2g")

    def test_export_downpayments_partner_fr(self):
        self.product_b.taxes_id = self.percent_tax(20.0).ids
        order = self._create_sale_order()
        order.order_line[1].product_uom_qty = 2
        downpayment_pct = 20
        payment_ctx = {
            "active_model": "sale.order",
            "active_ids": [order.id],
            "active_id": order.id,
        }
        wizard = (
            self.env["sale.advance.payment.inv"]
                .with_context(**payment_ctx)
                .create({
                    'advance_payment_method': 'percentage',
                    'amount': downpayment_pct,
                })
        )
        wizard.sudo().create_invoices()
        downpayment_invoice = order.invoice_ids
        downpayment_invoice.action_post()
        self._send_patched(downpayment_invoice)
        self._assert_invoice_ubl_file(downpayment_invoice, "ubl_21_fr_out_downpayment_invoice")

        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((downpayment_invoice.id,))],
                'date': self.fakenow.date(),
                'journal_id': downpayment_invoice.journal_id.id,
            }
        ).reverse_moves()
        downpayment_credit_note = downpayment_invoice.reversal_move_ids
        downpayment_credit_note.invoice_line_ids[0].price_unit = 100.0
        downpayment_credit_note.invoice_line_ids[1].price_unit = 40.0
        downpayment_credit_note.action_post()
        self._send_patched(downpayment_credit_note)
        self._assert_invoice_ubl_file(downpayment_credit_note, "ubl_21_fr_out_downpayment_credit_note")

        wizard = (
            self.env["sale.advance.payment.inv"]
                .with_context(**payment_ctx)
                .create({
                    'advance_payment_method': 'delivered',
                })
        )
        wizard.sudo().create_invoices()
        final_invoice = order.invoice_ids.filtered(
            lambda m: m.id not in downpayment_invoice.ids + downpayment_credit_note.ids
        )
        final_invoice.action_post()
        self._send_patched(final_invoice)
        self._assert_invoice_ubl_file(final_invoice, "ubl_21_fr_out_final_invoice")

    def test_import_downpayments_partner_fr(self):
        downpayment_invoice = self._import_invoice_as_attachment_on('ubl_21_fr_in_downpayment_invoice')
        self.assertEqual(downpayment_invoice.move_type, 'in_invoice')
        self.assertEqual(downpayment_invoice.amount_untaxed, 280.0)
        self.assertEqual(downpayment_invoice.amount_total, 336.0)
        self.assertRecordValues(downpayment_invoice.invoice_line_ids, [
            {'price_subtotal': 200.0, 'price_total': 240.0},
            {'price_subtotal': 80.0, 'price_total': 96.0},
        ])
        downpayment_refund = self._import_invoice_as_attachment_on('ubl_21_fr_in_downpayment_credit_note')
        self.assertEqual(downpayment_refund.move_type, 'in_refund')
        self.assertEqual(downpayment_refund.amount_untaxed, 140.0)
        self.assertEqual(downpayment_refund.amount_total, 168.0)
        self.assertRecordValues(downpayment_refund.invoice_line_ids, [
            {'price_subtotal': 100.0, 'price_total': 120.0},
            {'price_subtotal': 40.0, 'price_total': 48.0},
        ])
        # first type of final invoice: downpayments lines are copied in the final invoice.
        final_invoice_copied_lines = self._import_invoice_as_attachment_on('ubl_21_fr_in_final_invoice_copied_lines')
        self.assertEqual(final_invoice_copied_lines.move_type, 'in_invoice')
        self.assertEqual(final_invoice_copied_lines.amount_untaxed, 1260.00)
        self.assertEqual(final_invoice_copied_lines.amount_total, 1512.00)
        self.assertRecordValues(final_invoice_copied_lines.invoice_line_ids, [
            {'price_subtotal': 1000.0, 'price_total': 1200.0},
            {'price_subtotal': 400.0, 'price_total': 480.0},
            {'price_subtotal': -100.0, 'price_total': -120.0},
            {'price_subtotal': -40.0, 'price_total': -48.0},
        ])
        # second type of final invoice: downpayments lines are not present in the invoice.
        # downpayment amount is noted as a prepaid amount.
        # At import, we search for the downpayments and copy the lines from them.
        final_invoice_prepaid_amount = self._import_invoice_as_attachment_on('ubl_21_fr_in_final_invoice_prepaid_amount')
        self.assertEqual(final_invoice_prepaid_amount.move_type, 'in_invoice')
        self.assertEqual(final_invoice_prepaid_amount.amount_untaxed, 1260.00)
        self.assertEqual(final_invoice_prepaid_amount.amount_total, 1512.00)
        self.assertRecordValues(final_invoice_prepaid_amount.invoice_line_ids, [
            {'price_subtotal': 100.0, 'price_total': 120.0},
            {'price_subtotal': 40.0, 'price_total': 48.0},
            {'price_subtotal': -200.0, 'price_total': -240.0},
            {'price_subtotal': -80.0, 'price_total': -96.0},
            {'price_subtotal': 1000.0, 'price_total': 1200.0},
            {'price_subtotal': 400.0, 'price_total': 480.0},
        ])
