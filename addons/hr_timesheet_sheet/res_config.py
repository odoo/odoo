# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class hr_timesheet_settings(osv.osv_memory):
    _inherit = 'hr.config.settings'

    _columns = {
        'timesheet_range': fields.selection([('day','Day'),('week','Week'),('month','Month')],
            'Timesheet Range', help="Periodicity on which you validate your timesheets."),
        'timesheet_max_difference': fields.float('Timesheet Allowed Difference (Hours)',
            help="""Allowed difference in hours between the sign in/out and the timesheet
                computation for one sheet. Set this to 0 if you do not want any control."""),
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
