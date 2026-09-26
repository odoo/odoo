from unittest.mock import patch

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.point_of_sale.models.pos_config import PosConfig
from odoo.tests import tagged

from .common import TestL10nEsEdiTbaiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiTbaiPosFrontend(TestL10nEsEdiTbaiPosCommon, TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ensure_installed('l10n_es_pos')
        cls.main_pos_config.l10n_es_simplified_invoice_journal_id = cls.company_data['default_journal_sale']

    def test_tour_refund_simplified_invoice_uses_r5_without_popup(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.L10nEsEdiTbaiDocument._post_to_agency',
            return_value=(True, []),
        ):
            self.start_tour(
                f'/pos/ui?config_id={self.main_pos_config.id}',
                'l10n_es_edi_tbai_pos.tour_refund_simplified_invoice',
                login='pos_user',
            )

        orders = self.env['pos.order'].search([], order='id DESC', limit=2)
        refund, order = orders[0], orders[1]

        self.assertTrue(order.is_l10n_es_simplified_invoice)
        self.assertEqual(refund.l10n_es_tbai_refund_reason, 'R5')
        self.assertTrue(refund.is_l10n_es_simplified_invoice)
        self.assertTrue(refund.account_move.l10n_es_is_simplified)

    def test_tour_refund_explicit_invoice_shows_popup(self):
        partner = self.partner_b

        # Ensure the partner we want to select in the tour is loaded (without clicking "Search more")
        def mocked_get_limited_partners_loading(self):
            return [(partner.id,)]

        with patch.object(PosConfig, 'get_limited_partners_loading', mocked_get_limited_partners_loading):
            self.main_pos_config.with_user(self.pos_user).open_ui()
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.L10nEsEdiTbaiDocument._post_to_agency',
                return_value=(True, []),
            ):
                self.start_tour(
                    f'/pos/ui?config_id={self.main_pos_config.id}',
                    'l10n_es_edi_tbai_pos.tour_refund_explicit_invoice',
                    login='pos_user',
                )

        orders = self.env['pos.order'].search([], order='id DESC', limit=2)
        refund, order = orders[0], orders[1]

        self.assertFalse(order.is_l10n_es_simplified_invoice)
        self.assertEqual(refund.l10n_es_tbai_refund_reason, 'R2')
        self.assertFalse(refund.is_l10n_es_simplified_invoice)
        self.assertFalse(refund.account_move.l10n_es_is_simplified)
