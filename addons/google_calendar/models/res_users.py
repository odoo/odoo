# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class res_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'google_calendar_rtoken': fields.char('Refresh Token', copy=False),
        'google_calendar_token': fields.char('User token', copy=False),
        'google_calendar_token_validity': fields.datetime('Token Validity', copy=False),
        'google_calendar_last_sync_date': fields.datetime('Last synchro date', copy=False),
        'google_calendar_cal_id': fields.char('Calendar ID', help='Last Calendar ID who has been synchronized. If it is changed, we remove \
all links between GoogleID and Odoo Google Internal ID', copy=False)
    }
