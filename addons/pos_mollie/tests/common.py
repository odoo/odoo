from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestMollieCommon(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        payment_provider = cls.env["payment.provider"].create({"name": "Mollie Test", "code": "mollie", "mollie_api_key": "mockApiKey"})
        cls.main_pos_config.write({
            "payment_method_ids": [
                (0, 0, {
                    "name": "Mollie",
                    "type": "bank",
                    "payment_provider": "mollie",
                    "mollie_terminal_id": "MOLLIE123",
                    "mollie_payment_provider_id": payment_provider.id,
                    "payment_method_type": "terminal",
                    "journal_id": cls.bank_journal.id,
                }),
            ],
        })
        cls.mollie_payment_method = cls.main_pos_config.payment_method_ids.filtered(lambda pm: pm.payment_provider == "mollie")

    def setUp(self):
        super().setUp()
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.pos_session = self.main_pos_config.current_session_id
        self.mollie_payment_method = self.mollie_payment_method.with_user(self.pos_user)

    def _mollie_payment(self, status="open", **metadata):
        return {
            "id": "tr_test",
            "status": status,
            "metadata": {
                "payment_uuid": "uuid",
                "payment_method_id": self.mollie_payment_method.id,
                "pos_session_id": self.pos_session.id,
                **metadata,
            },
        }
