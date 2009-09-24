# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from xml import dom
from lxml import etree

from mx import DateTime
from mx.DateTime import now
import time

import netsvc
from osv import fields, osv
import ir


class one2many_mod(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if not context:
            context = {}
        res = {}
        num = name[4]
        for obj in obj.browse(cr, user, ids, context=context):
            res[obj.id] = []
            v = getattr(obj,'context'+num+'_id').id
            if v:
                ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id,'=',obj.id),('context_id','=',v)], limit=self._limit)
                for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
                    res[r[self._fields_id]].append( r['id'] )
        return res

class project_gtd_context(osv.osv):
    _name = "project.gtd.context"
    _description = "Contexts"
    _columns = {
        'name': fields.char('Context', size=64, required=True, select=1),
        'sequence': fields.integer('Sequence'),
        'project_default_id': fields.many2one('project.project', 'Default Project', required=True),
    }
    _defaults = {
        'sequence': lambda *args: 1
    }
    _order = "sequence, name"
project_gtd_context()


class project_gtd_timebox(osv.osv):
    _name = "project.gtd.timebox"
    _columns = {
        'name': fields.char('Timebox', size=64, required=True, select=1),
        'user_id': fields.many2one('res.users', 'User', required=True, select=1),
        'child_ids': fields.one2many('project.gtd.timebox', 'parent_id', 'Child Timeboxes'),
        'parent_id': fields.many2one('project.gtd.timebox', 'Parent Timebox'),
        'task_ids': fields.one2many('project.task', 'timebox_id', 'Tasks'),
        'type': fields.selection([('daily','Daily'),('weekly','Weekly'),('monthly','Monthly'),('other','Other')], 'Type', required=True),
        'task1_ids': one2many_mod('project.task', 'timebox_id', 'Tasks'),
        'task2_ids': one2many_mod('project.task', 'timebox_id', 'Tasks'),
        'task3_ids': one2many_mod('project.task', 'timebox_id', 'Tasks'),
        'task4_ids': one2many_mod('project.task', 'timebox_id', 'Tasks'),
        'task5_ids': one2many_mod('project.task', 'timebox_id', 'Tasks'),
        'task6_ids': one2many_mod('project.task', 'timebox_id', 'Tasks'),
        'context1_id': fields.many2one('project.gtd.context', 'Context 1', required=True),
        'context2_id': fields.many2one('project.gtd.context', 'Context 2'),
        'context3_id': fields.many2one('project.gtd.context', 'Context 3'),
        'context4_id': fields.many2one('project.gtd.context', 'Context 4'),
        'context5_id': fields.many2one('project.gtd.context', 'Context 5'),
        'context6_id': fields.many2one('project.gtd.context', 'Context 6'),
        'col_project': fields.boolean('Project'),
        'col_date_start': fields.boolean('Date Start'),
        'col_priority': fields.boolean('Priority'),
        'col_deadline': fields.boolean('Deadline'),
        'col_planned_hours': fields.boolean('Planned Hours'),
        'col_effective_hours': fields.boolean('Effective Hours'),
    }
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(project_gtd_timebox,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if (res['type']=='form') and ('record_id' in context):
            if context['record_id']:
                rec = self.browse(cr, uid, int(context['record_id']), context)
            else:
                iids = self.search(cr,uid, [('user_id','=',uid),('parent_id','=',False)], context=context)
                if len(iids):
                    rec = self.browse(cr, uid, int(iids[0]), context=context)
                else:
                    return res
            res['arch'] = """
    <form string="Daily Timebox">
        <field name="name" readonly="1"/>
        <notebook position="top">
            """
            for i in range(1,7):
                if not getattr(rec, 'context%d_id'%i):
                    continue
                res['arch']+= """
            <page string="%s">
                <field name="%s" colspan="4" nolabel="1">
                    <tree editable="bottom" colors="grey:state in ('done','pending');red:state=='cancelled'" string="Tasks">
                        <field name="name"/>
                """ % (getattr(rec, 'context%d_id'%(i,)).name.encode('utf-8'), 'task%d_ids'%(i,))
                if rec.col_project:
                    res['arch'] += '<field name="project_id" required="1"/>\n'
                if rec.col_date_start:
                    res['arch'] += '<field name="date_start"/>\n'
                if rec.col_priority:
                    res['arch'] += '<field name="priority"/>\n'
                if rec.col_deadline:
                    res['arch'] += '<field name="date_deadline"/>\n'
                if rec.col_planned_hours:
                    res['arch'] += '<field name="planned_hours"  widget="float_time" sum="Est. Hours"/>\n'
                if rec.col_effective_hours:
                    res['arch'] += '<field name="effective_hours"  widget="float_time" sum="%s"/>\n' % (_('Eff. Hours'),)
                res['arch'] += """
                        <field name="state" readonly="1"/>
                    </tree>
                </field>
            </page>
                """
            res['arch']+="""
        </notebook>
    </form>
            """
        doc = etree.XML(res['arch'])
        xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
        res['arch'] = xarch
        res['fields'] = xfields
        return res
    _defaults = {
        'type': lambda *args: 'daily',
        'col_project': lambda *args: True,
        'col_date_start': lambda *args: True,
        'col_priority': lambda *args: True,
        'col_deadline': lambda *args: False,
        'col_planned_hours': lambda *args: True,
        'col_effective_hours': lambda *args: False
    }
project_gtd_timebox()

class project_task(osv.osv):
    _inherit = "project.task"
    _columns = {
        'timebox_id': fields.many2one('project.gtd.timebox', "Timebox"),
        'context_id': fields.many2one('project.gtd.context', "Context"),
     }
    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default['timebox_id']=False
        default['context_id']=False
        return super(project_task,self).copy_data(cr, uid, id, default, context)
    def _get_context(self,cr, uid, ctx):
        ids = self.pool.get('project.gtd.context').search(cr, uid, [], context=ctx)
        return ids and ids[0] or False
    _defaults = {
        'context_id': _get_context
    }
    
    def next_timebox(self, cr, uid, ids, *args):
        for timebox in self.browse(cr, uid , ids):
            if timebox.timebox_id.type=='daily':
                timebox_ids = self.pool.get('project.gtd.timebox').search(cr, uid, [('type','=','weekly')])
                if timebox_ids:
                    self.write(cr, uid, ids, {'timebox_id' : timebox_ids[0]})
            if timebox.timebox_id.type=='weekly':
                timebox_ids = self.pool.get('project.gtd.timebox').search(cr, uid, [('type','=','monthly')])
                if timebox_ids:
                    self.write(cr, uid, ids, {'timebox_id' : timebox_ids[0]})
            if timebox.timebox_id.type=='monthly':
                timebox_ids = self.pool.get('project.gtd.timebox').search(cr, uid, [('type','=','other')])
                if timebox_ids:
                    self.write(cr, uid, ids, {'timebox_id':timebox_ids[0]})
        return True

    def prev_timebox(self, cr, uid, ids, *args):
        for timebox in self.browse(cr, uid , ids):
            if timebox.timebox_id.type=='other':
                timebox_ids = self.pool.get('project.gtd.timebox').search(cr, uid, [('type','=','monthly')])
                if timebox_ids:
                    self.write(cr, uid, ids, {'timebox_id' : timebox_ids[0]})
            if timebox.timebox_id.type=='monthly':
                timebox_ids = self.pool.get('project.gtd.timebox').search(cr, uid, [('type','=','weekly')])
                if timebox_ids:
                    self.write(cr, uid, ids, {'timebox_id' : timebox_ids[0]})
            if timebox.timebox_id.type=='weekly':
                timebox_ids = self.pool.get('project.gtd.timebox').search(cr, uid, [('type','=','daily')])
                if timebox_ids:
                    self.write(cr, uid, ids, {'timebox_id':timebox_ids[0]})
        return True
    
    # Override read for using this method if context set !!!
    #_order = "((55-ascii(coalesce(priority,'2')))*2 +  coalesce((date_start::date-current_date)/2,8))"
project_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

