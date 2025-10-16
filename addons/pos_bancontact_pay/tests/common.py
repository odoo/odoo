from odoo import Command

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestBancontactPay(TestPointOfSaleHttpCommon):
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
            "code": "BANCONTACT",
            "type": "bank",
            "company_id": cls.company.id,
            "currency_id": cls.eur_currency.id,
        })
        cls.bancontact_journal_2 = cls.env["account.journal"].create({
            "name": "Bancontact Journal 2",
            "code": "BANCONTACT2",
            "type": "bank",
            "company_id": cls.company_2.id,
            "currency_id": False,
        })

        # Payment Methods
        cls.payment_method_display = cls.env["pos.payment.method"].create({
            "name": "Bancontact - Display",
            "payment_method_type": "external_qr",
            "payment_provider": "bancontact_pay",
            "bancontact_usage": "display",
            "company_id": cls.company.id,
            "journal_id": cls.bancontact_journal.id,
            "bancontact_api_key": "display_api_key",
            "bancontact_ppid": "display_profile_id",
            "bancontact_test_mode": True,
        })
        cls.payment_method_display_2 = cls.env["pos.payment.method"].create({
            "name": "Bancontact - Display2",
            "payment_method_type": "external_qr",
            "payment_provider": "bancontact_pay",
            "bancontact_usage": "display",
            "company_id": cls.company_2.id,
            "journal_id": cls.bancontact_journal_2.id,
            "bancontact_api_key": "display_api_key",
            "bancontact_ppid": "display_profile_id",
            "bancontact_test_mode": True,
        })
        cls.payment_method_sticker_1 = cls.env["pos.payment.method"].create({
            "name": "Bancontact - Sticker 1",
            "payment_method_type": "external_qr",
            "payment_provider": "bancontact_pay",
            "bancontact_usage": "sticker",
            "bancontact_sticker_size": "L",
            "company_id": cls.company.id,
            "journal_id": cls.bancontact_journal.id,
            "bancontact_api_key": "sticker_api_key",
            "bancontact_ppid": "sticker_profile_id",
            "bancontact_test_mode": True,
        })
        cls.payment_method_sticker_2 = cls.env["pos.payment.method"].create({
            "name": "Bancontact - Sticker 2",
            "payment_method_type": "external_qr",
            "payment_provider": "bancontact_pay",
            "bancontact_usage": "sticker",
            "bancontact_sticker_size": "L",
            "company_id": cls.company.id,
            "journal_id": cls.bancontact_journal.id,
            "bancontact_api_key": "sticker_api_key",
            "bancontact_ppid": "sticker_profile_id",
            "bancontact_test_mode": True,
        })

        # Pos Config
        cls.main_pos_config.journal_id.currency_id = cls.eur_currency
        cls.main_pos_config.invoice_journal_id.currency_id = cls.eur_currency
        cls.main_pos_config.use_pricelist = False
        cls.main_pos_config.payment_method_ids = [
            Command.clear(),
            Command.link(cls.payment_method_display.id),
            Command.link(cls.payment_method_sticker_1.id),
            Command.link(cls.payment_method_sticker_2.id),
        ]
