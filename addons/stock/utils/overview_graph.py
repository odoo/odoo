import pytz
from datetime import timedelta

from odoo import fields


def calculate_date_category(record, datetime):
    """
    Assigns given datetime to one of the following categories:
    - "before"
    - "yesterday"
    - "today"
    - "day_1" (tomorrow)
    - "day_2" (the day after tomorrow)
    - "after"

    The categories are based on given record's timezone (e.g. "today" will last
    between 00:00 and 23:59 local time). The datetime itself is assumed to be
    in UTC. If the datetime is falsy, this function returns "none".
    """
    # TODO: calculate this once per list?
    start_today = fields.Datetime.context_timestamp(
        record, fields.Datetime.now()
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    start_yesterday = start_today + timedelta(days=-1)
    start_day_1 = start_today + timedelta(days=1)
    start_day_2 = start_today + timedelta(days=2)
    start_day_3 = start_today + timedelta(days=3)

    date_category = "none"

    if datetime:
        datetime = datetime.astimezone(pytz.UTC)
        if datetime < start_yesterday:
            date_category = "before"
        elif datetime >= start_yesterday and datetime < start_today:
            date_category = "yesterday"
        elif datetime >= start_today and datetime < start_day_1:
            date_category = "today"
        elif datetime >= start_day_1 and datetime < start_day_2:
            date_category = "day_1"
        elif datetime >= start_day_2 and datetime < start_day_3:
            date_category = "day_2"
        else:
            date_category = "after"

    return date_category
