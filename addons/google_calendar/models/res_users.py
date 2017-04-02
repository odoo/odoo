# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class User(models.Model):

    _inherit = 'res.users'

    google_calendar_rtoken = fields.Char('Refresh Token', copy=False)
    google_calendar_token = fields.Char('User token', copy=False)
    google_calendar_token_validity = fields.Datetime('Token Validity', copy=False)
    google_calendar_last_sync_date = fields.Datetime('Last synchro date', copy=False)
    google_calendar_cal_id = fields.Char('Calendar ID', copy=False, help='Last Calendar ID who has been synchronized. If it is changed, we remove all links between GoogleID and Odoo Google Internal ID')
