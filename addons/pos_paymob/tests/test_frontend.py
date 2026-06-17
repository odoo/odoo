# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests import Command, tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_paymob.controllers.main import PosPaymobController
from odoo.addons.pos_paymob.models.paymob_pos_request import PaymobPosRequest


@tagged("post_install", "-at_install")
class TestPosPaymobTour(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.write(
            {
                "payment_method_ids": [
                    Command.create(
                        {
                            "name": "Paymob",
                            "use_payment_terminal": "paymob",
                            "payment_method_type": "terminal",
                            "paymob_api_key": "test_api_key",
                            "paymob_terminal_identifier": "terminal_tour",
                            # Secret is required; the tour sends a dummy hmac and
                            # _verify_hmac is patched below to accept it.
                            "paymob_hmac_secret": "super_secret",
                            "paymob_test_mode": True,  # avoids depending on the company country
                            "journal_id": cls.bank_journal.id,
                        }
                    ),
                ],
            }
        )

    def test_tour_paymob_order_and_refund(self):
        # Settled, so paymob_send_reversal picks the refund endpoint over the void one.
        inquiry = {
            "id": 7000001,
            "is_settled": True,
            "success": True,
            "amount_cents": 1000,
        }
        with (
            patch.object(
                PaymobPosRequest, "create_order", return_value={"id": 7000001}
            ),
            patch.object(
                PaymobPosRequest,
                "send_refund",
                return_value={"message": "notification sent correctly"},
            ),
            patch.object(
                PaymobPosRequest,
                "send_void",
                return_value={"message": "notification sent correctly"},
            ),
            patch.object(PaymobPosRequest, "get_transaction", return_value=inquiry),
            patch.object(
                PosPaymobController,
                "_verify_hmac",
                staticmethod(lambda *args: True),
            ),
        ):
            self.start_pos_tour("paymob_order_and_refund")
