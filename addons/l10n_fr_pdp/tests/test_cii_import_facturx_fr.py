from odoo.tests import tagged

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPdpXmlCiiImport(TestL10nFrPdpCommon):

    @classmethod
    def subfolders(cls):
        return 'facturx', 'invoice', 'fr'

    def test_import_downpayments_partner_fr(self):
        self.percent_tax(20.0)
        downpayment_invoice = self._import_invoice_as_attachment_on('facturx_fr_in_downpayment_invoice')
        downpayment_invoice.action_post()
        self.assertEqual(downpayment_invoice.move_type, 'in_invoice')
        self.assertEqual(downpayment_invoice.amount_untaxed, 280.0)
        self.assertEqual(downpayment_invoice.amount_total, 336.0)
        self.assertRecordValues(downpayment_invoice.invoice_line_ids, [
            {'price_subtotal': 200.0, 'price_total': 240.0},
            {'price_subtotal': 80.0, 'price_total': 96.0},
        ])
        downpayment_refund = self._import_invoice_as_attachment_on('facturx_fr_in_downpayment_credit_note')
        downpayment_refund.action_post()
        self.assertEqual(downpayment_refund.move_type, 'in_refund')
        self.assertEqual(downpayment_refund.amount_untaxed, 140.0)
        self.assertEqual(downpayment_refund.amount_total, 168.0)
        self.assertRecordValues(downpayment_refund.invoice_line_ids, [
            {'price_subtotal': 100.0, 'price_total': 120.0},
            {'price_subtotal': 40.0, 'price_total': 48.0},
        ])
        # first type of final invoice: downpayments lines are copied in the final invoice.
        final_invoice_copied_lines = self._import_invoice_as_attachment_on('facturx_fr_in_final_invoice_copied_lines')
        final_invoice_copied_lines.action_post()
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
        final_invoice_prepaid_amount = self._import_invoice_as_attachment_on('facturx_fr_in_final_invoice_prepaid_amount')
        final_invoice_prepaid_amount.action_post()
        self.assertEqual(final_invoice_prepaid_amount.move_type, 'in_invoice')
        self.assertEqual(final_invoice_prepaid_amount.amount_untaxed, 1260.00)
        self.assertEqual(final_invoice_prepaid_amount.amount_total, 1512.00)
        self.assertRecordValues(final_invoice_prepaid_amount.invoice_line_ids, [
            {'price_subtotal': -200.0, 'price_total': -240.0},
            {'price_subtotal': -80.0, 'price_total': -96.0},
            {'price_subtotal': 100.0, 'price_total': 120.0},
            {'price_subtotal': 40.0, 'price_total': 48.0},
            {'price_subtotal': 1000.0, 'price_total': 1200.0},
            {'price_subtotal': 400.0, 'price_total': 480.0},
        ])
