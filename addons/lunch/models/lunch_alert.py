# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz

from odoo import api, fields, models
from odoo.osv import expression

from .lunch_supplier import float_to_time
from datetime import datetime, timedelta

from odoo.addons.base.models.res_partner import _tz_get

WEEKDAY_TO_NAME = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

class LunchAlert(models.Model):
    """ Alerts to display during a lunch order. An alert can be specific to a
    given day, weekly or daily. The alert is displayed from start to end hour. """
    _name = 'lunch.alert'
    _description = 'Lunch Alert'
    _order = 'write_date desc, id'

    name = fields.Char('Alert Name', required=True)
    message = fields.Html('Message', required=True)

    mode = fields.Selection([
        ('alert', 'Alert in app'),
        ('chat', 'Chat notification')], string='Display', default='alert')
    recipients = fields.Selection([
        ('everyone', 'Everyone'),
        ('last_week', 'Employee who ordered last week'),
        ('last_month', 'Employee who ordered last month'),
        ('last_year', 'Employee who ordered last year')], string='Recipients', default='everyone')
    notification_time = fields.Float(default=10.0, string='Notification Time')
    notification_moment = fields.Selection([
        ('am', 'AM'),
        ('pm', 'PM')], default='am', required=True)
    tz = fields.Selection(_tz_get, string='Timezone', required=True, default=lambda self: self.env.user.tz or 'UTC')

    until = fields.Date('Show Until')
    recurrency_monday = fields.Boolean('Monday', default=True)
    recurrency_tuesday = fields.Boolean('Tuesday', default=True)
    recurrency_wednesday = fields.Boolean('Wednesday', default=True)
    recurrency_thursday = fields.Boolean('Thursday', default=True)
    recurrency_friday = fields.Boolean('Friday', default=True)
    recurrency_saturday = fields.Boolean('Saturday', default=True)
    recurrency_sunday = fields.Boolean('Sunday', default=True)

    available_today = fields.Boolean('Is Displayed Today',
                                     compute='_compute_available_today', search='_search_available_today')

    active = fields.Boolean('Active', default=True)

    location_ids = fields.Many2many('lunch.location', string='Location')

    _sql_constraints = [
        ('notification_time_range',
            'CHECK(notification_time >= 0 and notification_time <= 12)',
            'Notification time must be between 0 and 12')
    ]

    @api.depends('recurrency_monday', 'recurrency_tuesday', 'recurrency_wednesday',
                 'recurrency_thursday', 'recurrency_friday', 'recurrency_saturday',
                 'recurrency_sunday')
    def _compute_available_today(self):
        today = fields.Date.context_today(self)
        fieldname = 'recurrency_%s' % (WEEKDAY_TO_NAME[today.weekday()])

        for alert in self:
            alert.available_today = alert.until > today if alert.until else True and alert[fieldname]

    def _search_available_today(self, operator, value):
        if (not operator in ['=', '!=']) or (not value in [True, False]):
            return []

        searching_for_true = (operator == '=' and value) or (operator == '!=' and not value)
        today = fields.Date.context_today(self)
        fieldname = 'recurrency_%s' % (WEEKDAY_TO_NAME[today.weekday()])

        return expression.AND([
            [(fieldname, operator, value)],
            expression.OR([
                [('until', '=', False)],
                [('until', '>' if searching_for_true else '<', today)],
            ])
        ])

    def _notify_chat(self):
        records = self.search([('mode', '=', 'chat'), ('active', '=', True)])

        today = fields.Date.today()
        now = fields.Datetime.now()

        for alert in records:
            notification_to = now.astimezone(pytz.timezone(alert.tz)).replace(second=0, microsecond=0, tzinfo=None)
            notification_from = notification_to - timedelta(minutes=5)
            send_at = datetime.combine(fields.Date.today(),
                float_to_time(alert.notification_time, alert.notification_moment))

            if alert.available_today and send_at > notification_from and send_at <= notification_to:
                order_domain = [('state', '!=', 'cancelled')]

                if alert.location_ids.ids:
                    order_domain = expression.AND([order_domain, [('user_id.last_lunch_location_id', 'in', alert.location_ids.ids)]])

                if alert.recipients != 'everyone':
                    weeks = 1

                    if alert.recipients == 'last_month':
                        weeks = 4
                    else:  # last_year
                        weeks = 52

                    delta = timedelta(weeks=weeks)
                    order_domain = expression.AND([order_domain, [('date', '>=', today - delta)]])

                orders = self.env['lunch.order'].search(order_domain).mapped('user_id')
                partner_ids = [user.partner_id.id for user in orders]
                if partner_ids:
                    self.env['mail.thread'].message_notify(body=alert.message, partner_ids=partner_ids)
