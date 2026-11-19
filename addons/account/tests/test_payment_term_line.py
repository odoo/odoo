from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import TransactionCase, tagged
from odoo import fields, Command


class TestAccountPaymentTermsLine(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pay_term_min1_months_after_on_the_15 = cls\
                .env['account.payment.term']\
                .create({
                    'name': "test_term_min1_months_after_on_the_15",
                    'line_ids': [
                        Command.create({
                            'value_amount': 100,
                            'value': 'percent',
                            'nb_days': -1,
                            'delay_type': 'months_after_on_the',
                            'days_next_month': 15,
                        }),
                    ],
        })

        cls.pay_term_0_months_after_on_the_15 = cls\
                .env['account.payment.term']\
                .create({
                    'name': "test_term_min1_months_after_on_the_15",
                    'line_ids': [
                        Command.create({
                            'value_amount': 100,
                            'value': 'percent',
                            'nb_days': 0,
                            'delay_type': 'months_after_on_the',
                            'days_next_month': 15,
                        }),
                    ],
        })

        cls.pay_term_1_months_after_on_the_15 = cls\
                .env['account.payment.term']\
                .create({
                    'name': "test_term_min1_months_after_on_the_15",
                    'line_ids': [
                        Command.create({
                            'value_amount': 100,
                            'value': 'percent',
                            'nb_days': 1,
                            'delay_type': 'months_after_on_the',
                            'days_next_month': 15,
                        }),
                    ],
        })

        cls.pay_term_0_months_after_on_the_30 = cls\
                .env['account.payment.term']\
                .create({
                    'name': "test_term_0_months_after_on_the_30",
                    'line_ids': [
                        Command.create({
                            'value_amount': 100,
                            'value': 'percent',
                            'nb_days': 0,
                            'delay_type': 'months_after_on_the',
                            'days_next_month': 30,
                        }),
                    ],
        })

        cls.pay_term_0_months_after_on_the_31 = cls\
                .env['account.payment.term']\
                .create({
                    'name': "test_term_0_months_after_on_the_31",
                    'line_ids': [
                        Command.create({
                            'value_amount': 100,
                            'value': 'percent',
                            'nb_days': 0,
                            'delay_type': 'months_after_on_the',
                            'days_next_month': 31,
                        }),
                    ],
        })

        cls.pay_term_1_months_after_on_the_0 = cls\
                .env['account.payment.term']\
                .create({
                    'name': "test_term_min1_months_after_on_the_15",
                    'line_ids': [
                        Command.create({
                            'value_amount': 100,
                            'value': 'percent',
                            'nb_days': 1,
                            'delay_type': 'months_after_on_the',
                            'days_next_month': 0,
                        }),
                    ],
        })

        cls.pay_term_1_months_after_on_the_1 = cls\
                .env['account.payment.term']\
                .create({
                    'name': "test_term_min1_months_after_on_the_15",
                    'line_ids': [
                        Command.create({
                            'value_amount': 100,
                            'value': 'percent',
                            'nb_days': 1,
                            'delay_type': 'months_after_on_the',
                            'days_next_month': 1,
                        }),
                    ],
        })

        cls.pay_term_1_months_after_on_the_2 = cls\
                .env['account.payment.term']\
                .create({
                    'name': "test_term_min1_months_after_on_the_15",
                    'line_ids': [
                        Command.create({
                            'value_amount': 100,
                            'value': 'percent',
                            'nb_days': 1,
                            'delay_type': 'months_after_on_the',
                            'days_next_month': 2,
                        }),
                    ],
        })

    def test_get_due_date_with_months_after_on_the_respects_max_days_in_month(self):
        """Test clipping to maximum days in a given month"""

        use_cases_31 = {
            '2026-11-20': '2026-11-30',
            '2026-10-20': '2026-10-31',
            '2026-02-02': '2026-02-28',
            '2028-02-02': '2028-02-29',
        }

        for due_date, expected_target_raw in use_cases_31.items():
            target = self.pay_term_0_months_after_on_the_31\
                    .line_ids._get_due_date(due_date)
            expected_target = fields.Date.from_string(expected_target_raw)

            self.assertEqual(expected_target, target)

        use_cases_30 = {
            '2026-11-20': '2026-11-30',
            '2026-10-20': '2026-10-30',
            '2026-02-02': '2026-02-28',
            '2028-02-02': '2028-02-29',
        }

        for due_date, expected_target_raw in use_cases_30.items():
            target = self.pay_term_0_months_after_on_the_30\
                    .line_ids._get_due_date(due_date)
            expected_target = fields.Date.from_string(expected_target_raw)

            with self.subTest(due_date=due_date, expected=expected_target_raw):
                self.assertEqual(expected_target, target)

    def test_get_due_date_with_months_after_on_the_works_with_month_offset(self):
        """Test various months offsets"""

        use_cases = {
            #              -1             0            +1 (months)
            '2026-11-20': ('2026-11-15', '2026-12-15', '2027-01-15'),  # after 15th
            '2026-12-15': ('2026-11-15', '2026-12-15', '2027-01-15'),  # at 15th
            '2026-02-04': ('2026-01-15', '2026-02-15', '2026-03-15'),  # before 15th
        }

        for due_date, expected_targets_raw in use_cases.items():
            i = -1
            for index, pay_term in enumerate((
                    self.pay_term_min1_months_after_on_the_15,
                    self.pay_term_0_months_after_on_the_15,
                    self.pay_term_1_months_after_on_the_15)):
                target = pay_term.line_ids._get_due_date(due_date)

                expected_target_raw = (expected_targets_raw)[index]
                expected_target = fields.Date.from_string(expected_target_raw)

                with self.subTest(
                        due_date=due_date,
                        expected=expected_target_raw,
                        nb_days_months=pay_term.line_ids.nb_days):
                    self.assertEqual(expected_target, target)

    def test_get_due_date_with_months_after_on_the_behaves_continuosly_in_respect_to_date(self):
        """Test continuous behaviour of the target date in respect to
        the days_next_month values. The value of days_next_month can be
        0, e.g. from 'days_end_of_month_on_the' delay type and we want to
        allow this value and return results close to the ones when
        days_next_month is set to value of 1."""

        use_cases = {
            # +1 month in all cases
            #               0             1             2 (days_next_month)
            '2026-10-20': ('2026-11-30', '2026-12-01', '2026-12-02'),
            '2026-11-20': ('2026-12-31', '2027-01-01', '2027-01-02'),
            '2026-12-15': ('2027-01-31', '2027-02-01', '2027-02-02'),
            '2026-02-04': ('2026-03-31', '2026-04-01', '2026-04-02'),
            '2026-02-03': ('2026-03-31', '2026-04-01', '2026-04-02'),
            # discontinuity in the following 2 lines is due to
            # rule where days_next_month is lower than due date date,
            # and that is intended
            '2026-02-02': ('2026-03-31', '2026-04-01', '2026-03-02'),
            '2028-02-01': ('2028-02-29', '2028-03-01', '2028-03-02'),
        }

        for due_date, expected_targets_raw in use_cases.items():
            i = -1
            for index, pay_term in enumerate((
                    self.pay_term_1_months_after_on_the_0,
                    self.pay_term_1_months_after_on_the_1,
                    self.pay_term_1_months_after_on_the_2)):
                target = pay_term.line_ids._get_due_date(due_date)

                expected_target_raw = (expected_targets_raw)[index]
                expected_target = fields.Date.from_string(expected_target_raw)

                with self.subTest(
                        due_date=due_date,
                        expected=expected_target_raw,
                        days_next_month=pay_term.line_ids.days_next_month):
                    self.assertEqual(expected_target, target)
