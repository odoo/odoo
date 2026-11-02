import math

from dateutil import rrule

MAX_RECURRENT_OCCURRENCES = 720

SELECT_FREQ_TO_RRULE = {
    'daily': rrule.DAILY,
    'weekly': rrule.WEEKLY,
    'monthly': rrule.MONTHLY,
    'yearly': rrule.YEARLY,
}

RRULE_FREQ_TO_SELECT = {v: k for k, v in SELECT_FREQ_TO_RRULE.items()}

RRULE_WEEKDAY_TO_FIELD = {
    rrule.MO.weekday: 'mon',
    rrule.TU.weekday: 'tue',
    rrule.WE.weekday: 'wed',
    rrule.TH.weekday: 'thu',
    rrule.FR.weekday: 'fri',
    rrule.SA.weekday: 'sat',
    rrule.SU.weekday: 'sun',
}

RRULE_WEEKDAYS = {'SUN': 'SU', 'MON': 'MO', 'TUE': 'TU', 'WED': 'WE', 'THU': 'TH', 'FRI': 'FR', 'SAT': 'SA'}
WEEKDAY_TO_RRULE = {
    'MON': rrule.MO, 'TUE': rrule.TU, 'WED': rrule.WE, 'THU': rrule.TH,
    'FRI': rrule.FR, 'SAT': rrule.SA, 'SUN': rrule.SU,
}

RRULE_TYPE_SELECTION = [
    ('daily', 'Days'),
    ('weekly', 'Weeks'),
    ('monthly', 'Months'),
    ('yearly', 'Years'),
]

RRULE_TYPE_SELECTION_UI = [
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
    ('custom', 'Custom')
]

END_TYPE_SELECTION = [
    ('count', 'Number of repetitions'),
    ('end_date', 'End date'),
    ('forever', 'Forever'),
]

MONTH_BY_SELECTION = [
    ('date', 'Date of month'),
    ('day', 'Day of month'),
]

WEEKDAY_SELECTION = [
    ('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'),
    ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday')
]

BYDAY_SELECTION = [
    ('1', 'First'), ('2', 'Second'), ('3', 'Third'),
    ('4', 'Fourth'), ('-1', 'Last')
]


def freq_to_select(rrule_freq):
    return RRULE_FREQ_TO_SELECT[rrule_freq]


def freq_to_rrule(freq):
    return SELECT_FREQ_TO_RRULE[freq]


def weekday_to_field(weekday_index):
    return RRULE_WEEKDAY_TO_FIELD.get(weekday_index)


def get_weekday_occurence(date):
    """
    :returns: ocurrence

    >>> get_weekday_occurence(date(2019, 12, 17))
    3  # third Tuesday of the month

    >>> get_weekday_occurence(date(2019, 12, 25))
    -1  # last Friday of the month
    """
    occurence_in_month = math.ceil(date.day / 7)
    if occurence_in_month in {4, 5}:  # fourth or fifth week on the month -> last
        return -1
    return occurence_in_month


def get_recurrence_values_from_date(date):
    """ Return the recurrence values repeating on the same weekday and day of month as `date`. """
    weekday_field_name = weekday_to_field(date.weekday())
    return {
        weekday_field_name: True,
        'weekday': weekday_field_name.upper(),
        'byday': str(get_weekday_occurence(date)),
        'day': date.day,
    }
