# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

class project_configuration(osv.osv_memory):
    _name = 'project.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_project_mrp': fields.boolean('generate tasks from sale orders',
            help ="""This feature automatically creates project tasks from service products in sale orders.
                More precisely, tasks are created for procurement lines with product of type 'Service',
                procurement method 'Make to Order', and supply method 'Produce'.
                This installs the module project_mrp."""),
        'module_pad': fields.boolean("use integrated collaborative note pads on task",
            help="""Lets the company customize which Pad installation should be used to link to new pads
                (by default, http://ietherpad.com/).
                This installs the module pad."""),
        'module_project_timesheet': fields.boolean("record timesheet lines per tasks",
            help="""This allows you to transfer the entries under tasks defined for Project Management to
                the timesheet line entries for particular date and user, with the effect of creating,
                editing and deleting either ways.
                This installs the module project_timesheet."""),
        'module_project_long_term': fields.boolean("manage resources palnning on gantt view",
            help="""A long term project management module that tracks planning, scheduling, and resource allocation.
                This installs the module project_long_term."""),
        'module_project_issue': fields.boolean("track issues and bug",
            help="""Provides management of issues/bugs in projects.
                This installs the module project_issue."""),
        'time_unit': fields.many2one('product.uom', 'working time unit', required=True,
            help="""This will set the unit of measure used in projects and tasks."""),
        'module_project_issue_sheet': fields.boolean("invoice working time on issues",
            help="""Provides timesheet support for the issues/bugs management in project.
                This installs the module project_issue_sheet."""),
        'group_tasks_work_on_tasks': fields.boolean("compute work activities on tasks",
            implied_group='project.group_tasks_work_on_tasks',
            help="Allows you to compute work on tasks."),
        'group_time_work_estimation_tasks': fields.boolean("manage time estimation on tasks",
            implied_group='project.group_time_work_estimation_tasks',
            help="Allows you to compute Time Estimation on tasks."),
        'group_manage_delegation_task': fields.boolean("allow task delegation",
            implied_group='project.group_delegate_task',
            help="Allows you to delegate tasks to other users."),
    }

    def get_default_time_unit(self, cr, uid, fields, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return {'time_unit': user.company_id.project_time_mode_id.id}

    def set_time_unit(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        user.company_id.write({'project_time_mode_id': config.time_unit.id})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
