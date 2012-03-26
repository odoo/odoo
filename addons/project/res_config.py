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

class project_configuration(osv.osv_memory):
    _inherit = 'project.config.settings'

    _columns = {
        'module_project_mrp': fields.boolean('Create tasks directly from a sale order',
            help ="""Automatically creates project tasks from procurement lines of type 'service'.
                This installs the module project_mrp."""),
        'module_pad': fields.boolean("Write task specifications on collaborative note pads",
            help="""Lets the company customize which Pad installation should be used to link to new pads
                (by default, http://ietherpad.com/).
                This installs the module pad."""),
        'module_project_timesheet': fields.boolean("Invoice working time on tasks",
            help="""This allows you to transfer the entries under tasks defined for Project Management to
                the timesheet line entries for particular date and user, with the effect of creating,
                editing and deleting either ways.
                This installs the module project_timesheet."""),
        'module_project_scrum': fields.boolean("Manage your project following Agile methodology",
            help="""This allows to implement all concepts defined by the scrum project management methodology for IT companies.
                    * Project with sprints, product owner, scrum master;
                    * Sprints with reviews, daily meetings, feedbacks;
                    * Product backlog;
                    * Sprint backlog.
                This installs the module project_scrum."""),
        'module_project_planning' : fields.boolean("Manage planning",
            help="""This module helps you to manage your plannings.
                Each department manager can know whether someone in their team has still unallocated time for a given
                planning (taking into consideration the validated leaves), or whether he/she still needs to encode tasks.
                This installs the module project_planning."""),
        'module_project_long_term': fields.boolean("Manage long term planning",
            help="""A long term project management module that tracks planning, scheduling, and resource allocation.
                This installs the module project_long_term."""),
        'module_project_issue_sheet': fields.boolean("Track and invoice issues working time",
            help="""Provides timesheet support for the issues/bugs management in project.
                This installs the module project_issue_sheet."""),
    }

    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False , type=[]):
        port = 0
        values = {}
        if server_type == 'pop':
            port = ssl and 995 or 110
        elif server_type == 'imap':
            port = ssl and 993 or 143
        else:
            values[type+'_server'] = ''
        values[type+'_port'] = port
        return {'value': values}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
