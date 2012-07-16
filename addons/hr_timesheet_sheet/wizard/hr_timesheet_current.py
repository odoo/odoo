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
import time

from osv import osv, fields
from tools.translate import _

class hr_timesheet_current_open(osv.osv_memory):
    _name = 'hr.timesheet.current.open'
    _description = 'hr.timesheet.current.open'

    def open_timesheet(self, cr, uid, ids, context=None):
        ts = self.pool.get('hr_timesheet_sheet.sheet')
        if context is None:
            context = {}
        view_type = 'form,tree'

        user_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], context=context)
        if not len(user_ids):
            raise osv.except_osv(_('Error !'), _('No employee defined for your user!'))
        ids = ts.search(cr, uid, [('user_id','=',uid),('state','=','draft'),('date_from','<=',time.strftime('%Y-%m-%d')), ('date_to','>=',time.strftime('%Y-%m-%d'))], context=context)

        if len(ids) > 1:
            view_type = 'tree,form'
            domain = "[('id','in',["+','.join(map(str, ids))+"]),('user_id', '=', uid)]"
        elif len(ids)==1:
            ts.write(cr, uid, ids, {'date_current': time.strftime('%Y-%m-%d')}, context=context)
            domain = "[('user_id', '=', uid)]"
        else:
            domain = "[('user_id', '=', uid)]"
        value = {
            'domain': domain,
            'name': _('Open Timesheet'),
            'view_type': 'form',
            'view_mode': view_type,
            'res_model': 'hr_timesheet_sheet.sheet',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        if len(ids) == 1:
            value['res_id'] = ids[0]
        return value

hr_timesheet_current_open()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: