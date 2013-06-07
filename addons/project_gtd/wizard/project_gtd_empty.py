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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class project_timebox_empty(osv.osv_memory):

    _name = 'project.timebox.empty'
    _description = 'Project Timebox Empty'
    _columns = {
        'name': fields.char('Name', size=32)
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        self._empty(cr, uid, context=context)
        pass

    def _empty(self, cr, uid, context=None):
        close = []
        up = []
        obj_tb = self.pool.get('project.gtd.timebox')
        obj_task = self.pool.get('project.task')

        if context is None:
            context = {}
        if not 'active_id' in context:
            return {}

        ids = obj_tb.search(cr, uid, [], context=context)
        if not len(ids):
            raise osv.except_osv(_('Error!'), _('No timebox child of this one!'))
        tids = obj_task.search(cr, uid, [('timebox_id', '=', context['active_id'])])
        for task in obj_task.browse(cr, uid, tids, context):
            if (task.state in ('cancel','done')) or (task.user_id.id <> uid):
                close.append(task.id)
            else:
                up.append(task.id)
        if up:
            obj_task.write(cr, uid, up, {'timebox_id':ids[0]})
        if close:
            obj_task.write(cr, uid, close, {'timebox_id':False})
        return {}

project_timebox_empty()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
