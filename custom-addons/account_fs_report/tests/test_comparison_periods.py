"""Enterprise parity: Balance Sheet comparison period dates + figures for every filter combo."""
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


def _compute_period_range(date_in_period, months_per_period, start_day=1, start_month=1):
    aligned = date_in_period - relativedelta(days=start_day - 1)
    year = aligned.year
    month_offset = aligned.month - start_month
    period_number = (month_offset // months_per_period) + 1
    if date_in_period < date(year, start_month, start_day):
        year -= 1
        period_number = ((12 + month_offset) // months_per_period) + 1
    month_delta = period_number * months_per_period
    end_date = date(year, start_month, 1) + relativedelta(months=month_delta, days=start_day - 2)
    start_date = date(year, start_month, 1) + relativedelta(
        months=month_delta - months_per_period, day=start_day
    )
    return start_date, end_date


def _shift_previous(date_to, period_type):
    ptype = 'year' if period_type in ('today', 'custom') else period_type
    months = {'quarter': 3, 'month': 1}.get(ptype, 12)
    date_from, _ = _compute_period_range(date_to, months)
    reference = date_from - relativedelta(days=1)
    _, new_to = _compute_period_range(reference, months)
    return new_to


def _community_columns(as_of, period_type, compare, number_period, period_order, custom_date=None):
    periods = []
    if compare == 'custom':
        periods = [custom_date]
    elif compare in ('previous_period', 'same_last_year'):
        cursor = as_of
        for _ in range(number_period):
            if compare == 'previous_period':
                cursor = _shift_previous(cursor, period_type)
            else:
                cursor = cursor - relativedelta(years=1)
            periods.append(cursor)
    cols = [as_of] + periods
    if period_order == 'ascending':
        cols = list(reversed(cols))
    return cols


def _growth_percent(first, second, green_on_positive=True):
    """Mirror Enterprise _compute_column_percent_comparison_data (percent mode)."""
    if abs(second) < 0.1:
        return 'n/a', 'muted'
    diff = first - second
    growth = round(diff / second * 100, 1)
    if abs(growth) < 0.05:
        return '0.0%', 'muted'
    mode = 'red' if (diff > 0) != green_on_positive else 'green'
    return f'{growth:.1f}%', mode


@tagged('post_install', '-at_install')
class TestComparisonPeriods(TransactionCase):

    def test_every_comparison_combo_matches_enterprise_dates(self):
        """Mirror Enterprise account.report._init_options_comparison period dates."""
        expected = {
            ('today', 'previous_period', 1, 'descending'): [date(2026, 11, 24), date(2025, 12, 31)],
            ('today', 'previous_period', 1, 'ascending'): [date(2025, 12, 31), date(2026, 11, 24)],
            ('today', 'previous_period', 2, 'descending'): [
                date(2026, 11, 24), date(2025, 12, 31), date(2024, 12, 31),
            ],
            ('today', 'previous_period', 2, 'ascending'): [
                date(2024, 12, 31), date(2025, 12, 31), date(2026, 11, 24),
            ],
            ('today', 'previous_period', 3, 'descending'): [
                date(2026, 11, 24), date(2025, 12, 31), date(2024, 12, 31), date(2023, 12, 31),
            ],
            ('today', 'previous_period', 3, 'ascending'): [
                date(2023, 12, 31), date(2024, 12, 31), date(2025, 12, 31), date(2026, 11, 24),
            ],
            ('today', 'same_last_year', 1, 'descending'): [date(2026, 11, 24), date(2025, 11, 24)],
            ('today', 'same_last_year', 1, 'ascending'): [date(2025, 11, 24), date(2026, 11, 24)],
            ('today', 'same_last_year', 2, 'descending'): [
                date(2026, 11, 24), date(2025, 11, 24), date(2024, 11, 24),
            ],
            ('today', 'same_last_year', 3, 'descending'): [
                date(2026, 11, 24), date(2025, 11, 24), date(2024, 11, 24), date(2023, 11, 24),
            ],
            ('month', 'previous_period', 1, 'descending'): [date(2026, 11, 30), date(2026, 10, 31)],
            ('month', 'same_last_year', 1, 'descending'): [date(2026, 11, 30), date(2025, 11, 30)],
            ('quarter', 'previous_period', 1, 'descending'): [date(2026, 9, 30), date(2026, 6, 30)],
            ('quarter', 'same_last_year', 1, 'descending'): [date(2026, 9, 30), date(2025, 9, 30)],
            ('year', 'previous_period', 1, 'descending'): [date(2026, 12, 31), date(2025, 12, 31)],
            ('year', 'same_last_year', 1, 'descending'): [date(2026, 12, 31), date(2025, 12, 31)],
            ('today', 'custom', 1, 'descending'): [date(2026, 11, 24), date(2026, 6, 30)],
            ('today', 'custom', 1, 'ascending'): [date(2026, 6, 30), date(2026, 11, 24)],
            # Specific Date defaults to as-of → duplicate dates must still yield two columns.
            ('today', 'custom_asof', 1, 'descending'): [date(2026, 11, 24), date(2026, 11, 24)],
        }
        as_of_by_type = {
            'today': date(2026, 11, 24),
            'month': date(2026, 11, 30),
            'quarter': date(2026, 9, 30),
            'year': date(2026, 12, 31),
        }
        for (ptype, compare, n, order), want in expected.items():
            as_of = as_of_by_type[ptype]
            if compare == 'custom':
                custom = date(2026, 6, 30)
                compare_key = 'custom'
            elif compare == 'custom_asof':
                custom = as_of
                compare_key = 'custom'
            else:
                custom = None
                compare_key = compare
            got = _community_columns(as_of, ptype, compare_key, n, order, custom)
            self.assertEqual(got, want, f'{ptype} {compare} n={n} {order}')

    def test_growth_column_math_matches_enterprise(self):
        """Descending uses col0 vs col1; ascending uses col1 vs col0; gop XOR color."""
        # ASSETS growth previous period on PARITY TEST CO fixtures.
        name, mode = _growth_percent(338000.0, 234000.0, green_on_positive=True)
        self.assertEqual((name, mode), ('44.4%', 'green'))
        name, mode = _growth_percent(84000.0, 40000.0, green_on_positive=False)
        self.assertEqual((name, mode), ('110.0%', 'red'))
        name, mode = _growth_percent(338000.0, 234000.0, green_on_positive=False)
        self.assertEqual((name, mode), ('44.4%', 'red'))
        # same_last_year bank subline
        name, mode = _growth_percent(114000.0, 74000.0, green_on_positive=True)
        self.assertEqual((name, mode), ('54.1%', 'green'))
        # zero base → n/a
        name, mode = _growth_percent(25000.0, 0.0, green_on_positive=True)
        self.assertEqual((name, mode), ('n/a', 'muted'))
        # identical → 0.0% muted
        name, mode = _growth_percent(114000.0, 114000.0, green_on_positive=True)
        self.assertEqual((name, mode), ('0.0%', 'muted'))

    def test_report_line_percent_of_current_assets(self):
        """Percentage of parent Current Assets (301k), not the asset_current leaf (25k)."""
        base = 301000.0  # CA section total
        cases = [
            (338000.0, True, '112.3%', 'green'),   # ASSETS
            (301000.0, True, '100.0%', ''),         # Current Assets section
            (114000.0, True, '37.9%', 'red'),       # Bank
            (150000.0, True, '49.8%', 'red'),       # Receivables
            (25000.0, True, '8.3%', 'red'),         # CAO leaf
            (12000.0, True, '4.0%', 'red'),         # Prepayments
            (30000.0, True, '10.0%', 'red'),        # Fixed Assets
            (7000.0, True, '2.3%', 'red'),          # Non-current Assets
            (84000.0, False, '27.9%', 'green'),     # LIABILITIES (gop False)
            (254000.0, True, '84.4%', 'red'),       # EQUITY
            (338000.0, False, '112.3%', 'red'),     # TLE (gop False)
        ]
        for value, gop, want_name, want_mode in cases:
            percentage = round(value * 100 / base, 1)
            if abs(percentage - 100.0) < 0.05:
                mode = ''
            else:
                mode = 'green' if ((percentage > 100.0) == gop) else 'red'
            self.assertEqual(
                (f'{percentage:.1f}%', mode),
                (want_name, want_mode),
                f'value={value} gop={gop}',
            )
