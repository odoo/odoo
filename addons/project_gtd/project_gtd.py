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

from xml import dom
from lxml import etree

from mx import DateTime
from mx.DateTime import now
import time
import tools
import netsvc
from osv import fields, osv
import ir

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
    _order = "sequence"
    _columns = {
        'name': fields.char('Timebox', size=64, required=True, select=1),
        'sequence': fields.integer('Sequence'),
        'icon': fields.selection(tools.icons, 'Icon', size=64),
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
        timebox_obj = self.pool.get('project.gtd.timebox')
        timebox_ids = timebox_obj.search(cr,uid,[])
        for task in self.browse(cr,uid,ids):
            timebox = task.timebox_id.id
            if timebox and  timebox_ids.index(timebox) != len(timebox_ids)-1 :
                index = timebox_ids.index(timebox)
            else:
                index = -1
            self.write(cr, uid, task.id, {'timebox_id': timebox_ids[index+1]})
        return True

    def prev_timebox(self, cr, uid, ids, *args):
        timebox_obj = self.pool.get('project.gtd.timebox')
        timebox_ids = timebox_obj.search(cr,uid,[])
        for task in self.browse(cr,uid,ids):
            timebox = task.timebox_id.id
            if timebox and  timebox_ids.index(timebox) != 0 :
                index = timebox_ids.index(timebox)
            else:
                index = len(timebox_ids)
            self.write(cr, uid, task.id, {'timebox_id': timebox_ids[index - 1]})
        return True
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(project_task,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        search_extended = False
        timebox_obj = self.pool.get('project.gtd.timebox')
        if res['type'] == 'search':
            tt = timebox_obj.browse(cr, uid, timebox_obj.search(cr,uid,[]))
            search_extended ='''<newline/><group col="%d">''' % (len(tt)+6,)
            search_extended += '''<filter domain="[('timebox_id','=', 0)]" icon="gtk-new" string="Inbox"/>'''
            search_extended += '''<separator orientation="vertical"/>'''
            for time in tt:
                if time.icon:
                    icon = time.icon
                else :
                    icon=""
                search_extended += ''' <filter domain="[('timebox_id','=', ''' + str(time.id) + ''')]" icon="''' + icon + '''" string="''' + time.name + '''"/>'''
            search_extended += '''
            <separator orientation="vertical"/>
            <field name="context_id" select="1" widget="selection"/> 
            <field name="priority" select="1"/>
            </group>
            </search> '''
        if search_extended:
            res['arch'] = res['arch'].replace('</search>',search_extended)
            attrs_sel = self.pool.get('project.gtd.context').name_search(cr, uid, '', [], context=context)
            context_id_info = self.pool.get('project.task').fields_get(cr, uid, ['context_id'])
            context_id_info['context_id']['selection'] = attrs_sel
            res['fields'].update(context_id_info)
        return res
 
    # Override read for using this method if context set !!!
    #_order = "((55-ascii(coalesce(priority,'2')))*2 +  coalesce((date_start::date-current_date)/2,8))"
project_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

