# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import pooler
class hr_timeshee_settings(osv.osv_memory):
    _name = 'human.resources.configuration'
    _inherit = 'human.resources.configuration'

    _columns = {
        'timesheet_range': fields.selection(
            [('day','Day'),('week','Week'),('month','Month')], 'Timesheet range',
            help="Periodicity on which you validate your timesheets."),
        'timesheet_max_difference': fields.float('Timesheet allowed difference(Hours)',
            help="Allowed difference in hours between the sign in/out and the timesheet " \
                 "computation for one sheet. Set this to 0 if you do not want any control."),
    }
  
    def default_get(self, cr, uid, fields, context=None):
        res = super(hr_timeshee_settings, self).default_get(cr, uid, fields, context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        res['timesheet_range']=user.company_id.timesheet_range 
        res['timesheet_max_difference']=user.company_id.timesheet_max_difference
        return res

    def set_timesheet_defaults(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids)[0]
        tm_range = wizard.timesheet_range
        tm_diff = wizard.timesheet_max_difference
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        user.company_id.write({'timesheet_range': tm_range,'timesheet_max_difference': tm_diff})  
        return {}  
