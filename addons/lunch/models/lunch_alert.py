# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, _


class LunchAlert(models.Model):
    """ Alerts to display during a lunch order. An alert can be specific to a
    given day, weekly or daily. The alert is displayed from start to end hour. """
    _name = 'lunch.alert'
    _description = 'Lunch Alert'
    _rec_name = 'message'

    display = fields.Boolean(compute='_compute_display_get')
    message = fields.Text('Message', required=True)
    alert_type = fields.Selection([('specific', 'Specific Day'),
                                   ('week', 'Every Week'),
                                   ('days', 'Every Day')],
                                  string='Recurrence', required=True, index=True, default='specific')
    partner_id = fields.Many2one('res.partner', string="Vendor",
                                 help="If specified, the selected vendor can be ordered only on selected days")
    specific_day = fields.Date('Day', default=fields.Date.context_today)
    monday = fields.Boolean('Monday')
    tuesday = fields.Boolean('Tuesday')
    wednesday = fields.Boolean('Wednesday')
    thursday = fields.Boolean('Thursday')
    friday = fields.Boolean('Friday')
    saturday = fields.Boolean('Saturday')
    sunday = fields.Boolean('Sunday')
    start_hour = fields.Float('Between', oldname='active_from', required=True, default=7)
    end_hour = fields.Float('And', oldname='active_to', required=True, default=23)
    active = fields.Boolean(default=True)

    @api.multi
    def name_get(self):
        return [(alert.id, '%s %s' % (_('Alert'), '#%d' % alert.id)) for alert in self]

    @api.depends('alert_type', 'specific_day', 'monday', 'tuesday', 'thursday',
                 'friday', 'saturday', 'sunday', 'start_hour', 'end_hour')
    def _compute_display_get(self):
        """
        This method check if the alert can be displayed today
        if alert type is specific : compare specific_day(date) with today's date
        if alert type is week : check today is set as alert (checkbox true) eg. self['monday']
        if alert type is day : True
        return : Message if can_display_alert is True else False
        """
        days_codes = {'0': 'sunday',
                      '1': 'monday',
                      '2': 'tuesday',
                      '3': 'wednesday',
                      '4': 'thursday',
                      '5': 'friday',
                      '6': 'saturday'}
        fullday = False
        now = datetime.datetime.now()
        if self.env.context.get('lunch_date'):
            # lunch_date is a fields.Date -> 00:00:00
            lunch_date = fields.Datetime.from_string(self.env.context['lunch_date'])
            # if lunch_date is in the future, planned lunch, ignore hours
            fullday = lunch_date > now
            now = max(lunch_date, now)
        mynow = fields.Datetime.context_timestamp(self, now)

        for alert in self:
            can_display_alert = {
                'specific': (str(alert.specific_day) == fields.Date.to_string(mynow)),
                'week': alert[days_codes[mynow.strftime('%w')]],
                'days': True
            }

            if can_display_alert[alert.alert_type]:
                hour_to = int(alert.end_hour)
                min_to = int((alert.end_hour - hour_to) * 60)
                to_alert = datetime.time(hour_to, min_to)
                hour_from = int(alert.start_hour)
                min_from = int((alert.start_hour - hour_from) * 60)
                from_alert = datetime.time(hour_from, min_from)

                if fullday or (from_alert <= mynow.time() <= to_alert):
                    alert.display = True
                else:
                    alert.display = False
