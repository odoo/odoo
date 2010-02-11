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

from lxml import etree
from mx import DateTime
from mx.DateTime import now
import time
from tools.translate import _

from osv import fields, osv
from tools.translate import _

class project_phase(osv.osv):
    _name = "project.phase"
    _description = "Project Phase"

    def _check_recursion(self,cr,uid,ids):
         obj_self = self.browse(cr, uid, ids[0])
         prev_ids = obj_self.previous_phase_ids
         next_ids = obj_self.next_phase_ids
         #it should nither be in prev_ids nor in next_ids
         if (obj_self in prev_ids) or (obj_self in next_ids):
             return False
         ids = [id for id in prev_ids if id in next_ids]

         #both prev_ids and next_ids must be unique
         if ids:
             return False
         #unrelated project

         prev_ids = [rec.id for rec in prev_ids]
         next_ids = [rec.id for rec in next_ids]

         #iter prev_ids
         while prev_ids:
             cr.execute('select distinct prv_phase_id from project_phase_previous_rel where phase_id in ('+','.join(map(str, prev_ids))+')')
             prv_phase_ids = filter(None, map(lambda x: x[0], cr.fetchall()))
             if obj_self.id in prv_phase_ids:
                 return False
             ids = [id for id in prv_phase_ids if id in next_ids]
             if ids:
                 return False
             prev_ids = prv_phase_ids

        #iter next_ids
         while next_ids:
             cr.execute('select distinct next_phase_id from project_phase_next_rel where phase_id in ('+','.join(map(str, next_ids))+')')
             next_phase_ids = filter(None, map(lambda x: x[0], cr.fetchall()))
             if obj_self.id in next_phase_ids:
                 return False
             ids = [id for id in next_phase_ids if id in prev_ids]
             if ids:
                 return False
             next_ids = next_phase_ids
         return True

    _columns = {
        'name': fields.char("Phase Name", size=64, required=True),
        'date_start': fields.datetime('Starting Date'),
        'date_end': fields.datetime('End Date'),
        'constraint_date_start': fields.datetime('Constraint Starting Date'),
        'constraint_date_end': fields.datetime('Constraint End Date'),
        'project_id': fields.many2one('project.project', 'Project', required=True),
        'next_phase_ids': fields.many2many('project.phase', 'project_phase_next_rel', 'phase_id', 'next_phase_id', 'Next Phases'),
        'previous_phase_ids': fields.many2many('project.phase', 'project_phase_previous_rel', 'phase_id', 'prv_phase_id', 'Previous Phases'),
        'duration': fields.float('Duration'),
        'product_uom': fields.many2one('product.uom', 'Duration UoM', help="UoM (Unit of Measure) is the unit of measurement for Duration"),
        'task_ids': fields.one2many('project.task', 'phase_id', "Project Tasks"),
        'resource_ids': fields.one2many('project.resource.allocation', 'phase_id', "Project Resources"),
     }

    _defaults = {
        'date_start': lambda *a: time.strftime('%Y-%m-%d'),
    }

    _order = "name"
    _constraints = [
        (_check_recursion,'Error ! Loops In Phases Not Allowed',['next_phase_ids','previous_phase_ids'])
    ]
project_phase()

class project_resource_allocation(osv.osv):
    _name = 'project.resource.allocation'
    _description = 'Project Resource Allocation'
    _rec_name = 'resource_id'
    _columns = {
#        'name': fields.char('Name',size = 64),
        'resource_id': fields.many2one('resource.resource', 'Resource', required=True),
        'phase_id': fields.many2one('project.phase', 'Project Phase', required=True),
        'useability': fields.float('Useability', help="Useability of this ressource for this project phase in percentage (=50%)"),
    }
    _defaults = {
        'useability': lambda *a: 100,
    }

project_resource_allocation()

class project(osv.osv):
    _inherit = "project.project"

    _columns = {
        'phase_ids': fields.one2many('project.phase', 'project_id', "Project Phases")
    }

project()

class task(osv.osv):
    _inherit = "project.task"

    _columns = {
        'phase_id': fields.many2one('project.phase', 'Project Phase')
    }
task()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

