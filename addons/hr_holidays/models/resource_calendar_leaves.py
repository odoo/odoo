# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class resource_calendar_leaves(osv.osv):
    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'holiday_id': fields.many2one("hr.holidays", "Leave Request"),
    }
