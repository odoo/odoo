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

import sys

from osv import fields, osv
import tools
from tools.translate import _

class project_gtd_context(osv.osv):
    _name = "project.gtd.context"
    _description = "Context"
    _columns = {
        'name': fields.char('Context', size=64, required=True, select=1, translate=1),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of contexts."),
    }
    _defaults = {
        'sequence': 1
    }
    _order = "sequence, name"

project_gtd_context()


class project_gtd_timebox(osv.osv):
    _name = "project.gtd.timebox"
    _order = "sequence"
    _columns = {
        'name': fields.char('Timebox', size=64, required=True, select=1, translate=1),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of timebox."),
        'icon': fields.selection(tools.icons, 'Icon', size=64),
        'todo_id': fields.many2one('crm.lead','TODO'),
    }

project_gtd_timebox()

class project_task(osv.osv):
    _inherit = "project.task"
    _columns = {
        'timebox_id': fields.many2one('project.gtd.timebox', "Timebox",help="Time-laps during which task has to be treated"),
        'context_id': fields.many2one('project.gtd.context', "Context",help="The context place where user has to treat task"),
     }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if not default:
            default = {}
        default['timebox_id'] = False
        default['context_id'] = False
        return super(project_task,self).copy_data(cr, uid, id, default, context)

    def _get_context(self,cr, uid, context=None):
        ids = self.pool.get('project.gtd.context').search(cr, uid, [], context=context)
        return ids and ids[0] or False

    _defaults = {
        'context_id': _get_context
    }
    def next_timebox(self, cr, uid, ids, *args):
        timebox_obj = self.pool.get('project.gtd.timebox')
        timebox_ids = timebox_obj.search(cr,uid,[])
        if not timebox_ids: return True
        for task in self.browse(cr,uid,ids):
            timebox = task.timebox_id.id
            if not timebox:
                self.write(cr, uid, task.id, {'timebox_id': timebox_ids[0]})
            elif timebox_ids.index(timebox) != len(timebox_ids)-1:
                index = timebox_ids.index(timebox)
                self.write(cr, uid, task.id, {'timebox_id': timebox_ids[index+1]})
        return True

    def prev_timebox(self, cr, uid, ids, *args):
        timebox_obj = self.pool.get('project.gtd.timebox')
        timebox_ids = timebox_obj.search(cr,uid,[])
        for task in self.browse(cr,uid,ids):
            timebox = task.timebox_id.id
            if timebox:
                if timebox_ids.index(timebox):
                    index = timebox_ids.index(timebox)
                    self.write(cr, uid, task.id, {'timebox_id': timebox_ids[index - 1]})
                else:
                    self.write(cr, uid, task.id, {'timebox_id': False})
        return True

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(project_task,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        search_extended = False
        timebox_obj = self.pool.get('project.gtd.timebox')
        access_pool = self.pool.get('ir.model.access')
        if (res['type'] == 'search') and access_pool.check_groups(cr, uid, "project_gtd.group_project_getting"):
            tt = timebox_obj.browse(cr, uid, timebox_obj.search(cr,uid,[]), context=context)
            search_extended ='''<newline/><group col="%d" expand="%d" string="%s">''' % (len(tt)+7,1,_('Getting Things Done'))
            search_extended += '''<filter domain="[('timebox_id','=', False)]" context="{'set_editable':True,'set_visible':True,'gtd_visible':True,'user_invisible':True}" icon="gtk-new" help="Undefined Timebox" string="%s" />''' % (_('Inbox'),)
            search_extended += '''<filter context="{'set_editable':True,'set_visible':True,'gtd_visible':True,'user_invisible':True}" icon="gtk-new" help="Getting things done" string="%s"/>''' % (_('GTD'),)
            search_extended += '''<separator orientation="vertical"/>'''
            for time in tt:
                if time.icon:
                    icon = time.icon
                else :
                    icon=""
                search_extended += '''<filter domain="[('timebox_id','=', ''' + str(time.id) + ''')]" icon="''' + icon + '''" string="''' + time.name + '''" context="{'gtd_visible':True, 'user_invisible': True}"/>'''
            search_extended += '''
            <separator orientation="vertical"/>
            <field name="context_id" select="1" widget="selection"/>
            </group>
            </search> '''
        if search_extended:
            res['arch'] = unicode(res['arch'], 'utf8').replace('</search>', search_extended)
            attrs_sel = self.pool.get('project.gtd.context').name_search(cr, uid, '', [], context=context)
            context_id_info = self.pool.get('project.task').fields_get(cr, uid, ['context_id'], context=context)
            context_id_info['context_id']['selection'] = attrs_sel
            res['fields'].update(context_id_info)
        return res

project_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
