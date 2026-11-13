from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_pk_edi_pos.tests.test_l10n_pk_edi_pos import OK_RESPONSE
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt


@tagged("post_install", "-at_install", "post_install_l10n")
class TestOrderReceiptL10n(TestPosOrderReceipt):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country("pk")
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.write({
            "l10n_pk_edi_pos_enabled": True,
            "l10n_pk_edi_pos_identifier": 110014,
            "l10n_pk_edi_pos_token": "prod-token",
            "l10n_pk_edi_pos_charge_service_fee": True,
        })
        cls.main_pos_config.payment_method_ids.l10n_pk_edi_pos_fbr_payment_code = "1"
        cls.example_simple_product.write({
            "hs_code": "1100.1010",
            "default_code": "PK-001",
        })
        cls.key_to_skip["image"].append("l10n_pk_edi_pos_fbr_logo")

    def test_receipt_data(self):
        with patch.object(self.env.registry["pos.order"], "_l10n_pk_edi_pos_connect_to_server", return_value=OK_RESPONSE):
            super().test_receipt_data()
