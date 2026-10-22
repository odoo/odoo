from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCzDomesticAccount(TransactionCase):

    def _get_domestic_account(self, account_number):
        return self.env['res.partner.bank'].new({'account_number': account_number})._l10n_cz_get_domestic_account()

    def test_local_account(self):
        self.assertEqual(
            self._get_domestic_account('19-2000145399/5500'),
            {'prefix': '19', 'number': '2000145399', 'bank_code': '5500'},
        )
        self.assertEqual(
            self._get_domestic_account(' 2000145399 / 0800 '),
            {'prefix': '', 'number': '2000145399', 'bank_code': '0800'},
        )

    def test_iban(self):
        self.assertEqual(
            self._get_domestic_account('CZ65 0800 0000 1920 0014 5399'),
            {'prefix': '19', 'number': '2000145399', 'bank_code': '0800'},
        )

    def test_invalid_modulo_11(self):
        for account_number in ('19-2000145398/5500', '18-2000145399/5500', 'CZ6050517873128883346693'):
            with self.subTest(account_number=account_number), self.assertRaisesRegex(ValidationError, 'modulo 11'):
                self._get_domestic_account(account_number)

    def test_invalid_iban(self):
        with self.assertRaisesRegex(ValidationError, 'IBAN does not pass the validation check'):
            self._get_domestic_account('CZ6608000000192000145399')
        with self.assertRaisesRegex(ValidationError, 'Czech IBAN'):
            self._get_domestic_account('BE68539007547034')

    def test_invalid_format(self):
        for account_number in ('', '2000145399', '1234567-2000145399/0800', 'abc/0800'):
            with self.subTest(account_number=account_number), self.assertRaisesRegex(ValidationError, 'Czech local account number'):
                self._get_domestic_account(account_number)
