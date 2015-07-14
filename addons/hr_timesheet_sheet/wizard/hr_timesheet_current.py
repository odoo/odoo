# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class hr_timesheet_current_open(osv.osv_memory):
    _name = 'hr.timesheet.current.open'
    _description = 'hr.timesheet.current.open'

    def open_timesheet(self, cr, uid, ids, context=None):
        ts = self.pool.get('hr_timesheet_sheet.sheet')
        if context is None:
            context = {}
        view_type = 'form,tree'

        ids = ts.search(cr, uid, [('user_id','=',uid),('state','in',('draft','new')),('date_from','<=',time.strftime('%Y-%m-%d')), ('date_to','>=',time.strftime('%Y-%m-%d'))], context=context)

        if len(ids) > 1:
            view_type = 'tree,form'
            domain = "[('id','in',["+','.join(map(str, ids))+"]),('user_id', '=', uid)]"
        elif len(ids)==1:
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
