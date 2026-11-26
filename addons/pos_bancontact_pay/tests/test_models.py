from odoo import Command
from odoo.exceptions import (
    ValidationError,
)

from odoo.addons.point_of_sale.tests.common import CommonPosTest


class TestModels(CommonPosTest):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.electronic_payment_display = cls.env["pos.electronic.payment"].create({
            "name": "Bancontact - Display",
            "integration_type": "qr",
            "payment_provider": "bancontact_pay",
            "bancontact_usage": "display",
        })
        cls.electronic_payment_sticker = cls.env["pos.electronic.payment"].create({
            "name": "Bancontact - Sticker",
            "integration_type": "qr",
            "payment_provider": "bancontact_pay",
            "bancontact_usage": "sticker",
        })
        cls.payment_method_display = cls.env["pos.payment.method"].create({
            "name": "Bancontact - Display",
            "electronic_payment_id": cls.electronic_payment_display.id,
            "type": "bank",
            "journal_id": cls.company_data['default_journal_bank'].id,
        })
        cls.payment_method_sticker = cls.env["pos.payment.method"].create({
            "name": "Bancontact - Sticker",
            "electronic_payment_id": cls.electronic_payment_sticker.id,
            "type": "bank",
            "journal_id": cls.company_data['default_journal_bank'].id,
        })

    def test_default_payment_methods(self):
        self.pos_config_eur.payment_method_ids = [Command.link(self.payment_method_display.id), Command.link(self.payment_method_sticker.id)]

        default_methods = self.env['pos.config']._default_payment_methods()
        bancontact_methods = [method for method in default_methods if method.payment_provider == 'bancontact_pay']

        # Has display methods
        display_methods = [method for method in bancontact_methods if method.bancontact_usage == 'display']
        self.assertEqual(len(display_methods), 1)

        # No sticker methods
        sticker_methods = [method for method in bancontact_methods if method.bancontact_usage == 'sticker']
        self.assertEqual(len(sticker_methods), 0)

    def test_one_bancontact_sticker_per_pos_config(self):
        test_config = self.env["pos.config"].create(
            {
                "name": "Test POS Config",
                "module_pos_restaurant": False,
            },
        )
        payment_method_sticker_2 = self.env["pos.payment.method"].create(
            {
                "name": "Bancontact - Sticker 2",
                "payment_method_type": "qr",
                "payment_provider": "bancontact_pay",
                "bancontact_usage": "sticker",
                "type": "bank",
                "company_id": self.company.id,
                "journal_id": self.company_data['default_journal_bank'].id,
            },
        )
        self.payment_method_sticker.config_ids = [Command.link(self.pos_config_eur.id)]

        # Assigning sticker already assigned to another POS config via pos.payment.method
        with self.assertRaises(ValidationError):
            self.payment_method_sticker.config_ids = [Command.link(test_config.id)]

        # Assigning sticker already assigned to another POS config via pos.config
        payment_method_sticker_2.config_ids = [Command.clear()]
        with self.assertRaises(ValidationError):
            test_config.payment_method_ids = [Command.link(self.payment_method_sticker.id)]

        # Assigning a new sticker to the POS config should work
        test_config.payment_method_ids = [Command.link(payment_method_sticker_2.id)]
