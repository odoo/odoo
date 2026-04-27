from contextlib import contextmanager

from odoo.addons.l10n_ec_edi.tests.common import TestEcEdiCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestEcEdiPosCommon(TestEcEdiCommon, TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

        cls.product_a.write({
            'available_in_pos': True,
        })

        # Set sri payment method for two PoS payment methods
        cls.cash_pm1.l10n_ec_sri_payment_id = cls.env['l10n_ec.sri.payment'].search([('code', '=', '01')], limit=1).id
        cls.bank_pm1.l10n_ec_sri_payment_id = cls.env['l10n_ec.sri.payment'].search([('code', '=', '19')], limit=1).id

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    def _create_order(self, ui_data):
        order_data = self.create_ui_order_data(**ui_data)
        results = self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].browse(results['pos.order'][0]['id'])
