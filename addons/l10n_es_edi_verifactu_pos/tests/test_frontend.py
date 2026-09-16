from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged

from .common import TestL10nEsEdiVerifactuPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuPosFrontend(TestL10nEsEdiVerifactuPosCommon, TestPointOfSaleHttpCommon):

    def _create_order(self, **kwargs):
        """Create the order to be refunded directly through the backend (like a prior PoS
        session would have), instead of selling it through the tour. This keeps the tour
        itself focused on the refund interaction under test, and avoids depending on the
        exact session order numbering ("001", "Shop - 000001", ...) to find it afterwards.
        """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.config = self.main_pos_config
        self.pos_session = self.main_pos_config.current_session_id
        self.currency = self.pos_session.currency_id
        self.pricelist = self.pos_session.config_id.pricelist_id

        order_data = self.create_ui_order_data(
            [(self.product, 1.0)],
            payments=[(self.bank_payment_method, 121.0)],
            **kwargs,
        )
        results = self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].browse(results['pos.order'][0]['id'])

    def test_tour_refund_not_invoiced_uses_r5_without_popup(self):
        with self._mock_zeep_registration_operation_certificate_issue():
            order = self._create_order()

            self.start_tour(
                f'/pos/ui?config_id={self.main_pos_config.id}',
                'l10n_es_edi_verifactu_pos.tour_refund_not_invoiced',
                login='pos_user',
            )

        self.assertFalse(order.to_invoice)
        refund = self.env['pos.order'].search([('id', '!=', order.id)], order='id desc', limit=1)
        self.assertEqual(refund.l10n_es_edi_verifactu_refund_reason, 'R5')

    def test_tour_refund_invoiced_shows_popup(self):
        with self._mock_zeep_registration_operation_certificate_issue():
            order = self._create_order(customer=self.partner_b, is_invoiced=True)

            self.start_tour(
                f'/pos/ui?config_id={self.main_pos_config.id}',
                'l10n_es_edi_verifactu_pos.tour_refund_invoiced',
                login='pos_user',
            )

        self.assertTrue(order.to_invoice)
        refund = self.env['pos.order'].search([('id', '!=', order.id)], order='id desc', limit=1)
        self.assertEqual(refund.account_move.l10n_es_edi_verifactu_refund_reason, 'R2')
