from unittest.mock import patch

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.point_of_sale.models.pos_config import PosConfig
from odoo.tests import tagged

from .common import TestL10nEsEdiVerifactuPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuPosFrontend(TestL10nEsEdiVerifactuPosCommon, TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.config = cls.main_pos_config  # i.e. not a restaurant config

        if cls.env['ir.module.module']._get('l10n_es_pos').state == 'installed':
            # Prevent creating automatic creation of simplified invoices
            cls.config.l10n_es_simplified_invoice_journal_id = False

    def test_tour_order_with_refund_reason(self):
        self.config.with_user(self.pos_user).open_ui()
        with self._mock_zeep_registration_operation_certificate_issue():
            self.start_tour(
                f'/pos/ui?config_id={self.config.id}',
                'l10n_es_edi_verifactu_pos.tour_with_refund_reason',
                step_delay=200,
                login='pos_user',
            )
        orders = self.env['pos.order'].search([], order='id DESC', limit=2)
        refund = orders[0]
        order = orders[1]

        self.assertTrue(order.l10n_es_edi_verifactu_document_ids.json_attachment_id)

        self.assertEqual(refund.l10n_es_edi_verifactu_refund_reason, 'R5')
        self.assertTrue(refund.l10n_es_edi_verifactu_document_ids.json_attachment_id)

    def test_tour_invoice_with_refund_reason(self):
        partner = self.partner_b

        # Ensure the partner we want to select in the tour is loaded (without clicking "Search more")
        def mocked_get_limited_partners_loading(self):
            return [(partner.id,)]

        with patch.object(PosConfig, 'get_limited_partners_loading', mocked_get_limited_partners_loading):
            self.config.with_user(self.pos_user).open_ui()
            with self._mock_zeep_registration_operation_certificate_issue():
                self.start_tour(
                    f'/pos/ui?config_id={self.config.id}',
                    'l10n_es_edi_verifactu_pos.tour_invoiced_with_refund_reason',
                    step_delay=200,
                    login='pos_user',
                )
        orders = self.env['pos.order'].search([], order='id DESC', limit=2)
        refund = orders[0]
        refund_move = refund.account_move
        order = orders[1]
        order_move = order.account_move

        self.assertTrue(order_move.l10n_es_edi_verifactu_document_ids.json_attachment_id)

        self.assertEqual(refund_move.l10n_es_edi_verifactu_refund_reason, 'R4')
        self.assertTrue(refund_move.l10n_es_edi_verifactu_document_ids.json_attachment_id)
