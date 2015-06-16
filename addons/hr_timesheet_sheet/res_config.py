# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class hr_timesheet_settings(osv.osv_memory):
    _inherit = 'hr.config.settings'

    _columns = {
        'timesheet_range': fields.selection([('day','Day'),('week','Week'),('month','Month')],
            'Validate timesheets every', help="Periodicity on which you validate your timesheets."),
        'timesheet_max_difference': fields.float('Allow a difference of time between timesheets and attendances of (in hours)',
            help='Allowed difference in hours between the sign in/out and the timesheet '
                 'computation for one sheet. Set this to 0 if you do not want any control.'),
    }

    def get_default_timesheet(self, cr, uid, fields, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return {
            'timesheet_range': user.company_id.timesheet_range,
            'timesheet_max_difference': user.company_id.timesheet_max_difference,
        }

    def set_default_timesheet(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        user.company_id.write({
            'timesheet_range': config.timesheet_range,
            'timesheet_max_difference': config.timesheet_max_difference,
        })
