# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    google_calendar_rtoken = fields.Char(string='Refresh Token')
    google_calendar_token = fields.Char(string='User token')
    google_calendar_token_validity = fields.Datetime(string='Token Validity')
    google_calendar_last_sync_date = fields.Datetime(string='Last synchro date')
    google_calendar_cal_id = fields.Char(string='Calendar ID', help='Last Calendar ID who has been synchronized. If it is changed, we remove \
all links between GoogleID and Odoo Google Internal ID')