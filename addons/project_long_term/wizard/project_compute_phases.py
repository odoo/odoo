# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
from openerp.tools.translate import _
from openerp.osv import fields, osv

class project_compute_phases(osv.osv_memory):
    _name = 'project.compute.phases'
    _description = 'Project Compute Phases'
    _columns = {
        'target_project': fields.selection([
            ('all', 'Compute All My Projects'),
            ('one', 'Compute a Single Project'),
            ], 'Action', required=True),
        'project_id': fields.many2one('project.project', 'Project')
    }
    _defaults = {
        'target_project': 'one'
    }

    def check_selection(self, cr, uid, ids, context=None):
        return self.compute_date(cr, uid, ids, context=context)

    def compute_date(self, cr, uid, ids, context=None):
        """
        Compute the phases for scheduling.
        """
        project_pool = self.pool.get('project.project')
        data = self.read(cr, uid, ids, [], context=context)[0]
        if not data['project_id'] and data['target_project'] == 'one':
            raise osv.except_osv(_('Error!'), _('Please specify a project to schedule.'))

        if data['target_project'] == 'one':
            project_ids = [data['project_id'][0]]
        else:
            project_ids = project_pool.search(cr, uid, [('user_id','=',uid)], context=context)

        if project_ids:
            project_pool.schedule_phases(cr, uid, project_ids, context=context)
        return self._open_phases_list(cr, uid, data, context=context)

    def _open_phases_list(self, cr, uid, data, context=None):
        """
        Return the scheduled phases list.
        """
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'project_long_term', 'act_project_phase')
        id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['target'] = 'current'
        project_id = data.get('project_id') and data.get('project_id')[0] or False
        result['context'] = {"search_default_project_id":project_id, "default_project_id":project_id, "search_default_current": 1}
        return result

project_compute_phases()
