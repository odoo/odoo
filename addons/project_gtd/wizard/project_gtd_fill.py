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

class project_timebox_fill(osv.osv_memory):

    _name = 'project.timebox.fill.plan'
    _description = 'Project Timebox Fill'
    _columns = {
        'timebox_id': fields.many2one('project.gtd.timebox', 'Get from Timebox', required=True),
        'timebox_to_id': fields.many2one('project.gtd.timebox', 'Set to Timebox', required=True),
        'task_ids': fields.many2many('project.task', 'project_task_rel', 'task_id', 'fill_id', 'Tasks selection')
    }

    def _get_from_tb(self, cr, uid, context=None):
        ids = self.pool.get('project.gtd.timebox').search(cr, uid, [], context=context)
        return ids and ids[0] or False

    def _get_to_tb(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'active_id' in context:
            return context['active_id']
        return False

    _defaults = {
         'timebox_id': _get_from_tb,
         'timebox_to_id': _get_to_tb,
    }

    def process(self, cr, uid, ids, context=None):
        if not ids:
            return {}
        data = self.read(cr, uid, ids, [], context=context)
        if not data[0]['task_ids']:
            return {}
        self.pool.get('project.task').write(cr, uid, data[0]['task_ids'], {'timebox_id':data[0]['timebox_to_id']})
        return {'type': 'ir.actions.act_window_close'}

project_timebox_fill()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
