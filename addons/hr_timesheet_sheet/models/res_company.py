# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'timesheet_range': fields.selection([('week','Week'),('month','Month')], 'Timesheet range',
            help="Periodicity on which you validate your timesheets."),
        'timesheet_max_difference': fields.float('Timesheet allowed difference(Hours)',
            help="Allowed difference in hours between the sign in/out and the timesheet " \
                 "computation for one sheet. Set this to 0 if you do not want any control."),
    }
    _defaults = {
        'timesheet_range': lambda *args: 'week',
        'timesheet_max_difference': lambda *args: 0.0
    }