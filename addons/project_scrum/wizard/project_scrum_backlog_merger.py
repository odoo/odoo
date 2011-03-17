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
from tools.translate import _

class project_scrum_backlog_merge(osv.osv_memory):
    _name = 'project.scrum.backlog.merge'
    _description = 'Merge Product Backlogs'
    _columns = {
        'project_id': fields.many2one('project.project', 'Project', help="Select project for the new product backlog"),
    }

    def check_backlogs(self, cr, uid, ids, context=None):
        backlog_obj = self.pool.get('project.scrum.product.backlog')
        mod_obj = self.pool.get('ir.model.data')
        p_list = []
        if context is None:
            context = {}
        #If only one product backlog selected for merging then show an exception
        if len(context['active_ids']) < 2:
            raise osv.except_osv(_('Warning'),_('Please select at least two product Backlogs'))
        #If any of the backlog state is done then it will show an exception
        for backlogs in backlog_obj.browse(cr, uid, context['active_ids'], context=context):
            p_list.append(backlogs.project_id.id)

        #For checking whether project id's are different or same.
        if len(set(p_list)) != 1:
            context.update({'scrum_projects': True})
            model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','scrum_merge_project_id_view')], context=context)
            resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
            return {
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'project.scrum.backlog.merge',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        return self.do_merge(cr, uid, ids, context=context)

    def do_merge(self, cr, uid, ids, context=None):
        backlog_obj = self.pool.get('project.scrum.product.backlog')
        task_obj = self.pool.get('project.task')
        task_lines = []
        new_exp_hour = []
        if context is None:
            context = {}
        #This will check product backlog's project id if different then will accept a new id provided by the user.
        if 'scrum_projects' in context:
            data = self.browse(cr, uid, ids, [])[0]
            if data.project_id.id == False:
                raise osv.except_osv(_('Warning'),_('Please select any Project.'))
            new_project_id = data.project_id.id
        else:
            p_id = backlog_obj.read(cr, uid, context['active_id'], ['project_id'])
            new_project_id = p_id['project_id'][0]
        #To merge note and description of backlogs
        new_note = ''
        new_description = ''
        for backlogs in backlog_obj.browse(cr, uid, context['active_ids'], context=context):
            if new_note:
                new_note += ' + '
                new_description += '\n\n'+('-'*50)+'\n'
            new_note += backlogs.name
            new_description += (backlogs.name or '') + '\n' + (backlogs.note or '')

            new_exp_hour.append(backlogs.expected_hours)
            for line in backlogs.tasks_id:
                task_lines.append(line.id)
        id_b = backlog_obj.create(cr, uid, {
            'name': new_note,
            'note': new_description,
            'project_id': new_project_id,
            'expected_hours': round(max(new_exp_hour))
        }, context=context)
        #To assing a new product backlog to merged tasks
        task_obj.write(cr, uid, task_lines, {'product_backlog_id': id_b})
        backlog_obj.unlink(cr, uid, context['active_ids'], context=context)
        return {'type': 'ir.actions.act_window_close'}

project_scrum_backlog_merge()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
