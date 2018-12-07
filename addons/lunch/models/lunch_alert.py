# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import pytz

from datetime import datetime, time

from odoo import api, fields, models

from odoo.osv import expression
from odoo.tools import float_round


WEEKDAY_TO_NAME = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

def float_to_time(hours, tz=None):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    res = time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)
    if tz:
        res = res.replace(tzinfo=pytz.timezone(tz))
    return res

def time_to_float(t):
    return float_round(t.hour + t.minute/60 + t.second/3600, precision_digits=2)


class LunchAlert(models.Model):
    """ Alerts to display during a lunch order. An alert can be specific to a
    given day, weekly or daily. The alert is displayed from start to end hour. """
    _name = 'lunch.alert'
    _description = 'Lunch Alert'
    _rec_name = 'message'

    message = fields.Text('Message', required=True)

    recurrency = fields.Selection([('once', 'Specific Day'), ('reccurent', 'Reccurent')], 'Recurrency', default='once')
    recurrency_from = fields.Float('From', default=7)
    recurrency_to = fields.Float('To', default=23)
    recurrency_date = fields.Date('Day', default=fields.Date.today())
    recurrency_date_from = fields.Datetime('from', compute='_compute_recurrency_date_from', store=True)
    recurrency_date_to = fields.Datetime('to', compute='_compute_recurrency_date_to', store=True)
    recurrency_monday = fields.Boolean('Monday')
    recurrency_tuesday = fields.Boolean('Tuesday')
    recurrency_wednesday = fields.Boolean('Wednesday')
    recurrency_thursday = fields.Boolean('Thursday')
    recurrency_friday = fields.Boolean('Friday')
    recurrency_saturday = fields.Boolean('Saturday')
    recurrency_sunday = fields.Boolean('Sunday')

    available_today = fields.Boolean('This is True when if the supplier is available today',
                                     compute='_compute_available_today', search='_search_available_today')

    @api.depends('recurrency_date', 'recurrency_from')
    def _compute_recurrency_date_from(self):
        for alert in self:
            if alert.recurrency_date and alert.recurrency_from:
                alert.recurrency_date_from = datetime.combine(alert.recurrency_date, float_to_time(alert.recurrency_from))

    @api.depends('recurrency_date', 'recurrency_to')
    def _compute_recurrency_date_to(self):
        for alert in self:
            if alert.recurrency_date and alert.recurrency_to:
                alert.recurrency_date_to = datetime.combine(alert.recurrency_date, float_to_time(alert.recurrency_to))

    @api.depends('recurrency', 'recurrency_date', 'recurrency_from', 'recurrency_to', 'recurrency_monday',
                 'recurrency_tuesday', 'recurrency_wednesday', 'recurrency_thursday',
                 'recurrency_friday', 'recurrency_saturday', 'recurrency_sunday')
    def _compute_available_today(self):
        now = fields.Datetime.now()

        for alert in self:
            time_from = float_to_time(alert.recurrency_from)
            time_to = float_to_time(alert.recurrency_to)

            if alert.recurrency == 'once':
                alert.available_today = (alert.recurrency_date_from <= now <= alert.recurrency_date_to)
            else:
                fieldname = 'recurrency_%s' % (WEEKDAY_TO_NAME[now.weekday()])
                alert.available_today = alert[fieldname] and (time_from <= now.time() <= time_to)

    def _search_available_today(self, operator, value):
        if (not operator in ['=', '!=']) or (not value in [True, False]):
            return []

        searching_for_true = (operator == '=' and value) or (operator == '!=' and not value)
        now = fields.Datetime.now()
        float_now = time_to_float(now.time())
        fieldname = 'recurrency_%s' % (WEEKDAY_TO_NAME[now.weekday()])

        if searching_for_true:
            specific = expression.AND([
                [('recurrency', '=', 'once')],
                [('recurrency_date_from', '<=', now)],
                [('recurrency_date_to', '>=', now)]
            ])
        else:
            specific = expression.AND([
                [('recurrency', '=', 'once')],
                expression.OR([
                    [('recurrency_date_from', '>=', now)],
                    [('recurrency_date_to', '<=', now)]
                ])
            ])

        recurrence = expression.AND([
            [(fieldname, operator, value)],
            [('recurrency_from', '<=' if searching_for_true else '>=', float_now)],
            [('recurrency_to', '>=' if searching_for_true else '<=', float_now)]
        ])

        return expression.OR([specific, recurrence])
