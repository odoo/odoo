
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMessageFormat(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_eur, cls.company_jpy, cls.company_bhd = cls.env['res.company'].create([
            {'name': 'EUR Company', 'currency_id': cls.env.ref('base.EUR').id},
            {'name': 'JPY Company', 'currency_id': cls.env.ref('base.JPY').id},
            {'name': 'BHD Company', 'currency_id': cls.env.ref('base.BHD').id},
        ])
        cls.tester = cls.env['mail.test.track.all'].create({'name': 'Tester'})

    def test_find_value_from_field_path_monetary(self):
        """Check the format of a monetary value, with and without a currency."""
        company_none = self.env['res.company']
        test_cases = [
            # 2 decimals, symbol after
            (self.company_eur, 150, '150.00 €'),
            (self.company_eur, 0, '0.00 €'),
            (self.company_eur, False, '0.00 €'),
            # 0 decimals, symbol before
            (self.company_jpy, 150, '¥ 150'),
            (self.company_jpy, 0, '¥ 0'),
            # 3 decimals, symbol after
            (self.company_bhd, 150, '150.000 BD'),
            (self.company_bhd, 0, '0.000 BD'),
            # no currency
            (company_none, 150, '150.0'),
            (company_none, 50.5, '50.5'),
            (company_none, False, '0.0'),
        ]
        for company, value, expected_value in test_cases:
            with self.subTest(currency=company.currency_id.name, value=value):
                self.tester.company_id = company
                self.tester.monetary_field = value
                res = self.tester._find_value_from_field_path('monetary_field')
                self.assertEqual(res, expected_value)

    def test_find_value_from_field_path_float(self):
        """Check the format of a float value, with and without digits."""
        test_cases = [
            # trailing zero decimals are hidden
            ('float_field', 50.5, '50.5'),
            ('float_field', 50, '50'),
            ('float_field', False, '0'),
            # custom digits precision, trailing zero decimals hidden as well
            ('float_field_with_digits', 50.123456789, '50.12345679'),
            ('float_field_with_digits', 50.5, '50.5'),
            ('float_field_with_digits', 0, '0'),
        ]
        for field_name, value, expected_value in test_cases:
            with self.subTest(field_name=field_name, value=value):
                self.tester[field_name] = value
                res = self.tester._find_value_from_field_path(field_name)
                self.assertEqual(res, expected_value)
