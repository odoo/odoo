# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import rrule, relativedelta


RRULE_FREQ = {
    ('daily', rrule.DAILY),
    ('weekly', rrule.WEEKLY),
    ('monthly', rrule.MONTHLY),
    ('yearly', rrule.YEARLY),
}
str2freq = {x[0]: x[1] for x in RRULE_FREQ}
freq2str = {x[1]: x[0] for x in RRULE_FREQ}

RRULE_WEEKDAYS = [
    ('mo', rrule.MO),
    ('tu', rrule.TU),
    ('we', rrule.WE),
    ('th', rrule.TH),
    ('fr', rrule.FR),
    ('sa', rrule.SA),
    ('su', rrule.SU),
]
wd2str = {x[1].weekday:x[0] for x in RRULE_WEEKDAYS}
str2day = {x[0]:x[1] for x in RRULE_WEEKDAYS}

def iso2date(dt_string, dt_start):
    dt = datetime.fromisoformat(dt_string)
    return datetime(dt.year, dt.month, dt.day, dt_start.hour, dt_start.minute, dt_start.second)

def RRULE(values, exdates=''):
    if not values.get('freq', False):
        return ''
    res = {}
    for key, value in values.items():
        if value and key in {'count', 'interval', 'until', 'dtstart'}:
            res[key] = value
        elif not value:
            continue
        elif key == 'freq':
            res['freq'] = str2freq[value]
        elif key in str2day and value:
            if 'byweekday' not in res:
                res['byweekday'] = []
            res['byweekday'] += [str2day[key].weekday]
        elif key == 'monthday':
            res['bymonthday'] = (value,)
        elif key == 'monthweekday_day':
            res['byweekday'] = ((str2day[value](values['monthweekday_n'])),)
    ruleset = rrule.rruleset()
    ruleset.rrule(rrule.rrule(**res))
    if exdates:
        for dt_string in exdates.split(','):
            if dt_string:
                ruleset.exdate(iso2date(dt_string, values['dtstart']))
    return ruleset

def occurenceRRULE(RRULESET, dtstart=None, dtend=None):
    if not RRULESET:
        return []
    rrule_rec = RRULESET._rrule[0]
    if not dtstart:
        dtstart = datetime.now()
    if rrule_rec._count:
        return RRULESET.xafter(dtstart)
    if not dtend:
        dtend = dtstart + relativedelta.relativedelta(years=1)
    return RRULESET.between(dtstart, dtend) or []

# def updateRRULE_drag(RRULE, dt1, dt2):
#     if not RRULE:
#         return ''
#     # This need to split the RRULE before
#     rule = parseRRULE(RRULE)
#     if rule['freq'] in ['daily', 'yearly']: # IDK If we use that
#         rule['dtstart'] = dt2
#     elif rule['freq'] == 'week':
#         rule[wd2str[dt1.weekday]] = False
#         rule[wd2str[dt2.weekday]] = True
#         rule['dtstart'] = dt2 - relativedelta.relativedelta(days=(dt2.weekday - dt1.weekday) % 7)
#     else:
#         rule['dtstart'] = dt2
#         rule['bymonthday'] = dt2.day
#         rule['bynmonthday'] = ()    # TODO SEE IF NEED MORE
#         rule['byweekday'] = ()      # TODO SEE IF NEED MORE
#     return updateRRULE(RRULE, rule)



# # For calendar connectors
# def parseRRULE(RRULE):
#     # TODO parse exdate
#     if not rrule:
#         return {}
#     set = rrule.rrulestr(RRULE, forceset=True)
#     rule = set._rrule[0]
#     res = {
#         'freq': freq2str[rule._freq],
#         'count': rule._count,
#         'interval': rule._interval,
#         'until': rule._until,
#         'dtstart': rule._dtstart,
#     }
#     if res['freq'] in ['daily', 'yearly']:
#         return res
#
#     if res['freq'] == 'weekly':
#         days = {wd2str[day]:True for day in rule._byweekday}
#         return {
#             **res,
#             **days,
#         }
#
#     ## MONTHLY
#     if rule._bymonthday:
#         res['monthday'] = rule._bymonthday[0]
#     elif rule._bynmonthday:
#         res['monthday'] = rule._bynmonthday[0]
#     elif rule._bynweekday:
#         res['monthweekday_n'] = rule._bynweekday[0][1]
#         res['monthweekday_day'] = wd2str[rule._bynweekday[0][0]]
#     return res
#
# def rruleset2str(RRULESET):
#     ret = str(RRULESET._rrule[0])
#     if RRULESET._exdate:
#         ret += "\nEXDATE:" + ','.join(date.strftime("%Y%m%dT%H%M%S") for date in RRULESET._exdate)
#     return ret
#
