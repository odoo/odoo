from odoo import Command

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestBancontactPay(TestPointOfSaleHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Currencies and company setup
        cls.eur_currency = cls.env.ref("base.EUR")
        cls.usd_currency = cls.env.ref("base.USD")
        cls.company.currency_id = cls.eur_currency

        # Second company for multi-company tests
        cls.company_2 = cls.env["res.company"].create({
            "name": "Test Currency Company",
            "currency_id": cls.eur_currency.id,
        })
        cls.env.user.company_ids |= cls.company_2

        # Journals
        cls.bancontact_journal = cls.env["account.journal"].create({
            "name": "Bancontact Journal",
            "code": "BANCO1",
            "type": "bank",
            "company_id": cls.company.id,
            "currency_id": cls.eur_currency.id,
        })
        cls.bancontact_journal_2 = cls.env["account.journal"].create({
            "name": "Bancontact Journal 2",
            "code": "BANCO22",
            "type": "bank",
            "company_id": cls.company_2.id,
            "currency_id": False,
        })

        # Bancontact Products
        cls.bancontact_product_display = cls.env["pos.bancontact.product"].create({
            "name": "Display Product",
            "api_key": "display_api_key",
            "ppid": "display_profile_id",
            "preprod": True,
            "usage": "display",
            "company_id": cls.company.id,
        })
        cls.bancontact_product_display_2 = cls.env["pos.bancontact.product"].create({
            "name": "Display Product 2",
            "api_key": "display_api_key_2",
            "ppid": "display_profile_id_2",
            "preprod": True,
            "usage": "display",
            "company_id": cls.company_2.id,
        })
        cls.bancontact_product_sticker = cls.env["pos.bancontact.product"].create({
            "name": "Sticker Product",
            "api_key": "sticker_api_key",
            "ppid": "sticker_profile_id",
            "preprod": True,
            "usage": "sticker",
            "company_id": cls.company.id,
        })
        cls.bancontact_sticker_1, cls.bancontact_sticker_2, cls.bancontact_sticker_3 = cls.env["pos.bancontact.sticker"].create([
            {"name": "Sticker 1", "product_id": cls.bancontact_product_sticker.id},
            {"name": "Sticker 2", "product_id": cls.bancontact_product_sticker.id},
            {"name": "Sticker 3", "product_id": cls.bancontact_product_sticker.id},
        ])

        # Payment Methods
        cls.payment_method_display = cls.env["pos.payment.method"].create({
            'type': 'bank',
            "name": "Bancontact - Display",
            "payment_method_type": "external_qr",
            "payment_provider": "bancontact_pay",
            "company_id": cls.company.id,
            "journal_id": cls.bancontact_journal.id,
            "bancontact_product_id": cls.bancontact_product_display.id,
        })
        cls.payment_method_display_2 = cls.env["pos.payment.method"].create({
            'type': 'bank',
            "name": "Bancontact - Display2",
            "payment_method_type": "external_qr",
            "payment_provider": "bancontact_pay",
            "company_id": cls.company_2.id,
            "journal_id": cls.bancontact_journal_2.id,
            "bancontact_product_id": cls.bancontact_product_display_2.id,
        })
        cls.payment_method_sticker_1 = cls.env["pos.payment.method"].create({
            "name": "Bancontact - Sticker 1",
            "payment_method_type": "external_qr",
            "payment_provider": "bancontact_pay",
            "type": "bank",
            "company_id": cls.company.id,
            "journal_id": cls.bancontact_journal.id,
            "bancontact_product_id": cls.bancontact_product_sticker.id,
            "bancontact_sticker_id": cls.bancontact_sticker_1.id,
        })
        cls.payment_method_sticker_2 = cls.env["pos.payment.method"].create({
            "name": "Bancontact - Sticker 2",
            "payment_method_type": "external_qr",
            "payment_provider": "bancontact_pay",
            "type": "bank",
            "company_id": cls.company.id,
            "journal_id": cls.bancontact_journal.id,
            "bancontact_product_id": cls.bancontact_product_sticker.id,
            "bancontact_sticker_id": cls.bancontact_sticker_2.id,
        })

        # Pos Config
        cls.main_pos_config.journal_id.currency_id = cls.eur_currency
        cls.main_pos_config.use_pricelist = False
        cls.main_pos_config.payment_method_ids = [
            Command.clear(),
            Command.link(cls.payment_method_display.id),
            Command.link(cls.payment_method_sticker_1.id),
            Command.link(cls.payment_method_sticker_2.id),
        ]
