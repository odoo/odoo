from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.pos_bancontact_pay.tests.common import TestBancontactPay


@tagged("post_install", "-at_install")
class TestModels(TestBancontactPay):

    def test_check_unsupported_kiosks(self):
        kiosk_config = self.env["pos.config"].create(
            {
                "name": "Kiosk POS Config",
                "self_ordering_mode": "kiosk",
                "payment_method_ids": [Command.clear()],
            },
        )
        with self.assertRaises(ValidationError):
            kiosk_config.payment_method_ids = [Command.link(self.payment_method_display.id)]
        with self.assertRaises(ValidationError):
            self.payment_method_display.config_ids = [Command.link(kiosk_config.id)]
