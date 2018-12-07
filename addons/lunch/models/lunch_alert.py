# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


WEEKDAY_TO_NAME = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

class LunchAlert(models.Model):
    """ Alerts to display during a lunch order. An alert can be specific to a
    given day, weekly or daily. The alert is displayed from start to end hour. """
    _name = 'lunch.alert'
    _description = 'Lunch Alert'
    _rec_name = 'message'

    message = fields.Html('Message', required=True)

    until = fields.Date('Show Until')
    recurrency_monday = fields.Boolean('Monday')
    recurrency_tuesday = fields.Boolean('Tuesday')
    recurrency_wednesday = fields.Boolean('Wednesday')
    recurrency_thursday = fields.Boolean('Thursday')
    recurrency_friday = fields.Boolean('Friday')
    recurrency_saturday = fields.Boolean('Saturday')
    recurrency_sunday = fields.Boolean('Sunday')

    available_today = fields.Boolean('Is Displayed Today',
                                     compute='_compute_available_today', search='_search_available_today')

    active = fields.Boolean(default=True)

    location_ids = fields.Many2many('lunch.location', string='Location')

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
