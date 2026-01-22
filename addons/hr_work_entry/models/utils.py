from datetime import timedelta

from odoo import fields


def date_list_to_ranges(dates: list) -> list[dict]:
    """
    Converts a list of dates to a list of ranges, considering dates to be
    neighbors if they are maximum a day apart
    e.g.:
        input: [20/12/20205, 21/12/2025, 10/10/2010]
        output: [
        {start: 20/12/2025, stop: 21/12/2025},
        {start: 10/10/2010, stop: 10/10/2010},
    ]
    """
    def _is_in_next_day(date_a, date_b) -> bool:
        return date_a <= date_b and date_b <= date_a + timedelta(days=1)

    # special case. no date means no ranges
    if not dates:
        return []

    ranges = []
    # so that we iterate day by day in order
    dates = sorted(fields.Date.to_date(date) for date in dates)
    range_start = dates[0]
    for i in range(1, len(dates) + 1):
        if i < len(dates) and _is_in_next_day(dates[i - 1], dates[i]):
            continue
        # range end found. Adding it to the list
        ranges.append({
            'start': range_start,
            'stop': dates[i - 1],
        })
        if i < len(dates):  # avoid out of bounds if end of iteration
            range_start = dates[i]
    return ranges


def remove_days_from_range(range: dict, days: list) -> list[dict]:
    """
    Returns a list of range, being the result of removing `days` from
    `range`.
    e.g.:
        input:
        days = [date(2025, 5, 4)]
        range = {'start': date(2025, 5, 1), 'stop': date(2025, 5, 10)}
        output:
        [
            {'start': date(2025, 5, 1), 'stop': date(2025, 5, 3)},
            {'start': date(2025, 5, 5), 'stop': date(2025, 5, 10)},
        ]
    """
    days = sorted(fields.Date.to_date(day) for day in days)
    days = filter(lambda d: range['start'] <= d <= range['stop'], days)
    start = range['start']
    ranges = []
    for day in days:
        if day == start:
            start = day + timedelta(days=1)
            continue
        ranges.append({'start': start, 'stop': day - timedelta(days=1)})
        start = day + timedelta(days=1)
    if start <= range['stop']:
        ranges.append({'start': start, 'stop': range['stop']})
    return ranges
