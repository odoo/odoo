from odoo import fields
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestL10nPeCurrencyRates(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()

        cls.date_yesterday = fields.Date.to_date('2023-10-01')
        cls.date_today = fields.Date.to_date('2023-10-02')

        cls.rate_yesterday = cls.env['res.currency.rate'].create({
            'name': cls.date_yesterday,
            'rate': 3.5,
            'currency_id': cls.company_data['currency'].id,
            'company_id': cls.company_data['company'].id,
        })

        cls.rate_today = cls.env['res.currency.rate'].create({
            'name': cls.date_today,
            'rate': 3.8,
            'currency_id': cls.company_data['currency'].id,
            'company_id': cls.company_data['company'].id,
        })

    def test_pe_bcrp_currency_rate_fetching(self):
        """
        Test that when the provider is 'bcrp', the rate fetched includes the current day (<=).
        For other providers, it should fetch the previous day's rate (<).
        """
        self.company_data['company'].currency_provider = 'ecb'
        rates_standard = self.company_data['currency']._get_rates(self.company_data['company'], self.date_today)
        self.assertEqual(
            rates_standard.get(self.company_data['currency'].id)[0],
            3.5,
            "Standard behavior should fetch the previous day's rate (exclusive strict < check)."
        )

        self.company.currency_provider = 'bcrp'
        rates_bcrp = self.company_data['currency']._get_rates(self.company_data['company'], self.date_today)
        self.assertEqual(
            rates_bcrp.get(self.company_data['currency'].id)[0],
            3.8,
            "SUNAT (bcrp) behavior should fetch the current day's rate (inclusive <= check)."
        )
