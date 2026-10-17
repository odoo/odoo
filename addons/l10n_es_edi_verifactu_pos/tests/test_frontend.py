from unittest.mock import patch

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.point_of_sale.models.pos_config import PosConfig
from odoo.tests import tagged

from .common import TestL10nEsEdiVerifactuPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuPosFrontend(TestL10nEsEdiVerifactuPosCommon, TestPointOfSaleHttpCommon):

    def test_tour_refund_not_invoiced_uses_r5_without_popup(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self._mock_zeep_registration_operation_certificate_issue():
            self.start_tour(
                f'/pos/ui?config_id={self.main_pos_config.id}',
                'l10n_es_edi_verifactu_pos.tour_refund_not_invoiced',
                login='pos_user',
            )

        orders = self.env['pos.order'].search([], order='id DESC', limit=2)
        refund, order = orders[0], orders[1]

        self.assertFalse(order.to_invoice)
        self.assertEqual(refund.l10n_es_edi_verifactu_refund_reason, 'R5')

    def test_tour_refund_invoiced_shows_popup(self):
        partner = self.partner_b

        # Ensure the partner we want to select in the tour is loaded (without clicking "Search more")
        def mocked_get_limited_partners_loading(self):
            return [(partner.id,)]

        with patch.object(PosConfig, 'get_limited_partners_loading', mocked_get_limited_partners_loading):
            self.main_pos_config.with_user(self.pos_user).open_ui()
            with self._mock_zeep_registration_operation_certificate_issue():
                self.start_tour(
                    f'/pos/ui?config_id={self.main_pos_config.id}',
                    'l10n_es_edi_verifactu_pos.tour_refund_invoiced',
                    login='pos_user',
                )

        orders = self.env['pos.order'].search([], order='id DESC', limit=2)
        refund, order = orders[0], orders[1]

        self.assertTrue(order.to_invoice)
        self.assertEqual(refund.account_move.l10n_es_edi_verifactu_refund_reason, 'R2')
