# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from unittest.mock import patch

from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception()


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEmploymentHero(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.request_get_path = 'odoo.addons.l10n_employment_hero.models.res_company.requests.get'

        # Update address of company to Australia
        cls.company_data['company'].write({
            "street": "Bennelong Point",
            "city": "Sydney",
            "state_id": cls.env.ref("base.state_au_2").id,
            "country_id": cls.env.ref("base.au").id,
            "zip": "2000",
        })

        # Update config
        cls.config = cls.env["res.config.settings"].create({
            "employment_hero_api_key": "KEYPAY_API_KEY",
            "employment_hero_base_url": "https://keypay.yourpayroll.com.au",
            "employment_hero_enable": True,
            "employment_hero_identifier": "KEYPAY_BUSINESS_ID",
            "employment_hero_lock_date": datetime.date(2023, 12, 31),
            "employment_hero_journal_id": cls.env['account.journal'].search([
                ('code', '=', 'MISC'), ('company_id', '=', cls.company.id)
            ], limit=1).id,
        })
        cls.config.execute()

        # bis account should take priority as they have a kp_account_identifier
        cls.keypay_accounts = cls.env['account.account'].create([{
            'name': 'Test 1',
            'code': '1234',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 1 bis',
            'employment_hero_account_identifier': '1234',
            'code': '9999',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 2 bis',
            'employment_hero_account_identifier': '5678',
            'code': '8888',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 4',
            'code': 'efgh',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 6',
            'code': 'mnop',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 7',
            'code': 'qrst',
            'account_type': 'liability_current',
        }])

        cls.tax = cls.env['account.tax'].create({
            'name': 'Test Tax 1',
            'amount': 10.0,
            'employment_hero_tax_identifier': 'VAT1',
        })

    def test_payrun_no_new_entries(self):
        """ Emulate a fetch where there have been no new entries since the lock date.
        We expect it to work but not create any moves.
        """
        with patch(self.request_get_path, side_effect=lambda url, **kwargs: MockResponse([], 200)):
            self.config.action_eh_payroll_fetch_payrun()
            moves = self.env['account.move'].search([('employment_hero_payrun_identifier', '!=', False)])
            self.assertEqual(len(moves), 0)

    def test_payrun_during_lockdate(self):
        """ If a payrun happens to be on the lock date, it should not be fetched. """
        def mocked_get(url, *args, **kwargs):
            # First call will fetch the payrun.
            if '/payrun' in url:
                data = [{
                    "id": 7027852,
                    "payPeriodEnding": "2020-07-31T07:07:38",
                    "datePaid": "2020-07-31T00:00:00",
                    "isFinalised": True,
                }]
            # It will then call get for each payrun to get the journal entry lines.
            else:
                data = [{
                    "amount": 635.0,
                    "reference": "Wages and Salary for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "5678",
                    "isCredit": True,
                    "isDebit": False,
                }, {
                    "amount": -720.0,
                    "reference": "Wages Expense for pay period ending 09/08/2020",
                    "taxCode": "W1",
                    "accountCode": "1234",
                    "isCredit": False,
                    "isDebit": True,
                }, {
                    "amount": 85.0,
                    "reference": "PAYG Liability for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "efgh",
                    "isCredit": True,
                    "isDebit": False,
                }]

            return MockResponse(data, 200)

        with patch(self.request_get_path, side_effect=mocked_get):
            self.config.action_eh_payroll_fetch_payrun()
            moves = self.env['account.move'].search([('employment_hero_payrun_identifier', '!=', False)])
            # We expect a single journal entry, with the three lines above
            self.assertEqual(len(moves), 1)
            self.assertEqual(len(moves.line_ids), 3)

    def test_payrun_large_amount(self):
        """ Test to fetch payruns with more than 100 of them to ensure pagination is working as intended. """
        def mocked_get(url, *args, **kwargs):
            if '/payrun' in url and 'skip=0' in url:
                data = []
                for i in range(100):
                    data.append({
                        "id": i,
                        "payPeriodEnding": "2020-07-31T07:07:38",
                        "datePaid": "2020-07-31T00:00:00",
                        "isFinalised": False,  # Left to false on purpose to avoid generating account moves.
                    })
            elif '/payrun' in url and 'skip=100' in url:
                # Just one more for the sake of testing.
                data = [{
                    "id": 101,
                    "payPeriodEnding": "2020-07-31T07:07:38",
                    "datePaid": "2020-07-31T00:00:00",
                    "isFinalised": False,
                }]
            else:
                # The linter will complain about data below without the else, and the 500 will cause a raise
                return MockResponse([], 500)

            return MockResponse(data, 200)

        with patch(self.request_get_path, side_effect=mocked_get) as mocked_get:
            self.config.action_eh_payroll_fetch_payrun()
            # We expect two calls to the get method. Once for the first 100 records, and once more for the last one.
            self.assertEqual(mocked_get.call_count, 2)

    def test_payrun_entries(self):
        """ Fetches payruns and validate the date inside the entries. """
        def mocked_get(url, *args, **kwargs):
            # First call will fetch the payrun.
            if '/payrun' in url:
                data = [{
                    "id": 1,
                    "payPeriodEnding": "2020-07-31T07:07:38",
                    "datePaid": "2020-07-31T00:00:00",
                    "isFinalised": True,
                }, {
                    "id": 2,
                    "payPeriodEnding": "2020-08-21T07:07:38",
                    "datePaid": "2020-08-21T00:00:00",
                    "isFinalised": True,
                }]
            # It will then call get for each payrun to get the journal entry lines.
            elif '/journal/1' in url:
                data = [{
                    "amount": 615.0,
                    "reference": "Wages and Salary for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "5678",
                    "isCredit": True,
                    "isDebit": False,
                }, {
                    "amount": -700.0,
                    "reference": "Wages Expense for pay period ending 09/08/2020",
                    "taxCode": "VAT1",
                    "accountCode": "1234",
                    "isCredit": False,
                    "isDebit": True,
                }, {
                    "amount": 85.0,
                    "reference": "PAYG Liability for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "efgh",
                    "isCredit": True,
                    "isDebit": False,
                }, {
                    "amount": -68.4,
                    "reference": "Superannuation Expense for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "mnop",
                    "isCredit": False,
                    "isDebit": True,
                }, {
                    "amount": 68.4,
                    "reference": "Superannuation Liability for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "qrst",
                    "isCredit": True,
                    "isDebit": False,
                }]
            else:
                data = [{
                    "units": 0.0,
                    "amount": 1996.0,
                    "reference": "Wages and Salary for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "5678",
                    "isCredit": True,
                    "isDebit": False,
                }, {
                    "amount": -2880.0,
                    "reference": "Wages Expense for pay period ending 09/08/2020",
                    "taxCode": "VAT1",
                    "accountCode": "1234",
                    "isCredit": False,
                    "isDebit": True,
                }, {
                    "amount": 884.0,
                    "reference": "PAYG Liability for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "efgh",
                    "isCredit": True,
                    "isDebit": False,
                }, {
                    "amount": -273.6,
                    "reference": "Superannuation Expense for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "mnop",
                    "isCredit": False,
                    "isDebit": True,
                }, {
                    "amount": 273.6,
                    "reference": "Superannuation Liability for pay period ending 09/08/2020",
                    "taxCode": "None",
                    "accountCode": "qrst",
                    "isCredit": True,
                    "isDebit": False,
                }]

            return MockResponse(data, 200)

        with patch(self.request_get_path, side_effect=mocked_get):
            self.config.action_eh_payroll_fetch_payrun()
            moves = self.env['account.move'].search([('employment_hero_payrun_identifier', '!=', False)])
            self.assertEqual(len(moves), 2)

            # Validate the first entry
            first_entry = moves[0]
            self.assertEqual(len(first_entry.line_ids), 6)
            self.assertEqual(first_entry.date, datetime.date(2020, 8, 21))
            self.assertRecordValues(first_entry.line_ids, [{
                'credit': 1996.0,
                'debit': 0.0,
                'tax_ids': [],
                'account_id': self.keypay_accounts[2].id  # Test 2 bis
            }, {
                'credit': 0.0,
                'debit': 2618.18,
                'tax_ids': [self.tax.id],
                'account_id': self.keypay_accounts[1].id  # Test 1 bis
            }, {
                'credit': 884.0,
                'debit': 0.0,
                'tax_ids': [],
                'account_id': self.keypay_accounts[3].id  # Test 4
            }, {
                'credit': 0.0,
                'debit': 273.6,
                'tax_ids': [],
                'account_id': self.keypay_accounts[4].id  # Test 6
            }, {
                'credit': 273.6,
                'debit': 0.0,
                'tax_ids': [],
                'account_id': self.keypay_accounts[5].id  # Test 7
            }, {
                'credit': 0.0,
                'debit': 261.82,
                'tax_ids': [],
                'account_id': self.keypay_accounts[1].id  # Test 1 bis
            }])
            # Validate the second entry
            second_entry = moves[1]
            self.assertEqual(len(second_entry.line_ids), 6)
            self.assertEqual(second_entry.date, datetime.date(2020, 7, 31))
            self.assertRecordValues(second_entry.line_ids, [{
                'credit': 615.0,
                'debit': 0.0,
                'tax_ids': [],
                'account_id': self.keypay_accounts[2].id  # Test 2 bis
            }, {
                'credit': 0.0,
                'debit': 636.36,
                'tax_ids': [self.tax.id],
                'account_id': self.keypay_accounts[1].id  # Test 1 bis
            }, {
                'credit': 85.0,
                'debit': 0.0,
                'tax_ids': [],
                'account_id': self.keypay_accounts[3].id  # Test 4
            }, {
                'credit': 0.0,
                'debit': 68.4,
                'tax_ids': [],
                'account_id': self.keypay_accounts[4].id  # Test 6
            }, {
                'credit': 68.4,
                'debit': 0.0,
                'tax_ids': [],
                'account_id': self.keypay_accounts[5].id  # Test 7
            }, {
                'credit': 0.0,
                'debit': 63.64,
                'tax_ids': [],
                'account_id': self.keypay_accounts[1].id  # Test 1 bis
            }])
