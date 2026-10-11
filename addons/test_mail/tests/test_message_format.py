
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMessageFormat(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.euro_currency = cls.env.ref('base.EUR')
        cls.jpy_currency = cls.env.ref('base.JPY')
        cls.lyd_currency = cls.env.ref('base.LYD')
        cls.tester_monetary = cls.env['mail.test.track.all'].create({
            'name': 'EUR Tester',
            'monetary_field': '150'
        })
        # Create company to use as env.company
        cls.default_company = cls.env['res.company'].create({
            'name': 'Default Company',
            'currency_id': cls.lyd_currency.id
        })

    def test_find_value_from_field_path_monetary(self):
        """ Check the format of the return in case of monetary value (Digits after comma """
        test_cases = [
            (self.euro_currency, '150.00'),  # 2 decimals
            (self.jpy_currency, '150'),  # 0 decimals
            (self.lyd_currency, '150.000'),  # 3 decimals
        ]
        for currency, expected_value in test_cases:
            with self.subTest(currency=currency.name):
                self.tester_monetary.currency_id = currency
                res = self.tester_monetary._find_value_from_field_path('monetary_field')
                self.assertEqual(res, expected_value)

    def test_find_value_from_field_path_monetary_empty_value(self):
        """ Check the behavior when a monetary field is False """
        tester_no_amount = self.env['mail.test.track.all'].create({
            'name': 'Tester No Amount',
            'monetary_field': False,
        })
        tester_no_amount.currency_id = self.euro_currency
        res = tester_no_amount._find_value_from_field_path('monetary_field')
        self.assertEqual(res, '0.00')

    def test_find_value_from_field_path_monetary_zero_value(self):
        """ Check an amount of 0 is correcly formated"""
        tester = self.tester_monetary
        tester.monetary_field = 0.0
        test_cases = [
            (self.lyd_currency, '0.000'),  # 3 decimals
            (self.jpy_currency, '0'),  # 0 decimals
        ]
        for currency, expected_value in test_cases:
            with self.subTest(currency=currency.name):
                tester.currency_id = currency
                res = tester._find_value_from_field_path('monetary_field')
                self.assertEqual(res, expected_value)

    def test_find_value_from_field_path_monetary_missing_currency(self):
        """ Check default format is currency_id is not present on record"""
        tester_no_currency = self.env['mail.test.track.all'].create({
            'name': 'Tester No Currency',
            'monetary_field': 50,
        })
        tester_no_currency.currency_id = None
        tester_no_currency.company_id = self.default_company  # Test fallback to env.company.currency_id
        res = tester_no_currency._find_value_from_field_path('monetary_field')
        self.assertEqual(res, '50.000')

    def test_find_value_from_field_path_float(self):
        """Check that a float is correctly formatted"""
        tester = self.env['mail.test.track.all'].create({
            'name': 'Tester Float',
            'float_field': 50.5,
            'float_field_with_digits': 50.5,
        })
        test_cases = [
            ('float_field', '50.50'),  # Default precision
            ('float_field_with_digits', '50.50000000'),  # Custom digits precision
        ]
        for field_name, expected_value in test_cases:
            with self.subTest(field_name=field_name):
                res = tester._find_value_from_field_path(field_name)
                self.assertEqual(res, expected_value)
