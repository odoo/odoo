from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged

from .common import TestL10nEsEdiVerifactuPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuPosFrontend(TestL10nEsEdiVerifactuPosCommon, TestPointOfSaleHttpCommon):

    def test_tour_order_with_refund_reason(self):
        # Remove the simplified invoice journal so that the orders are not invoiced by default
        self.config.l10n_es_simplified_invoice_journal_id = False

        self.config.with_user(self.pos_user).open_ui()
        with self._mock_zeep_registration_operation_certificate_issue():
            self.start_tour(
                f'/pos/ui?config_id={self.config.id}',
                'l10n_es_edi_verifactu_pos.tour_with_refund_reason',
                step_delay=200,  # TODO:
                login='pos_user',
            )
        orders = self.env['pos.order'].search([], order='id DESC', limit=2)
        refund = orders[0]
        order = orders[1]

        self.assertTrue(order.l10n_es_edi_verifactu_document_ids.json_attachment_base64)

        self.assertEqual(refund.l10n_es_edi_verifactu_refund_reason, 'R1')
        self.assertTrue(refund.l10n_es_edi_verifactu_document_ids.json_attachment_base64)

    def test_tour_invoice_with_refund_reason(self):
        # If the simplified invoice journal is set then all orders are invoiced by default
        self.assertTrue(self.config.l10n_es_simplified_invoice_journal_id)

        self.config.with_user(self.pos_user).open_ui()
        with self._mock_zeep_registration_operation_certificate_issue():
            self.start_tour(
                f'/pos/ui?config_id={self.config.id}',
                'l10n_es_edi_verifactu_pos.tour_with_refund_reason',
                step_delay=200,  # TODO:
                login='pos_user',
            )
        orders = self.env['pos.order'].search([], order='id DESC', limit=2)
        refund = orders[0]
        refund_move = refund.account_move
        order = orders[1]
        order_move = order.account_move

        self.assertTrue(order_move.l10n_es_edi_verifactu_document_ids.json_attachment_base64)

        self.assertEqual(refund_move.l10n_es_edi_verifactu_refund_reason, 'R1')
        self.assertTrue(refund_move.l10n_es_edi_verifactu_document_ids.json_attachment_base64)
