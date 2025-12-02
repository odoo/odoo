from unittest.mock import patch
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import Command
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestQFPayPoS(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.currency_id = cls.env.ref("base.HKD")
        cls.main_pos_config.use_pricelist = False
        cls.main_pos_config.write({
            "payment_method_ids": [
                Command.create({
                    "name": "QFPay",
                    "qfpay_pos_key": "my_qfpay_pos_key",
                    "qfpay_notification_key": "my_qfpay_notification_key",
                    "use_payment_terminal": "qfpay",
                    "payment_method_type": "terminal",
                    "qfpay_payment_type": "card_payment",
                    "journal_id": cls.bank_journal.id,
                }),
            ],
        })

    def test_tour_qfpay_order_and_refund(self):
        with patch('odoo.addons.pos_qfpay.controllers.main.consteq', lambda a, b: True):
            self.start_pos_tour('qfpay_order_and_refund')
