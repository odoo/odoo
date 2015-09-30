# -*- coding: utf-8 -*-
from openerp.osv import osv, fields

class res_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'google_calendar_rtoken': fields.char('Refresh Token'),
        'google_calendar_token': fields.char('User token'),
        'google_calendar_token_validity': fields.datetime('Token Validity'),
        'google_calendar_last_sync_date': fields.datetime('Last synchro date'),
        'google_calendar_cal_id': fields.char('Calendar ID', help='Last Calendar ID who has been synchronized. If it is changed, we remove \
all links between GoogleID and Odoo Google Internal ID')
    }
