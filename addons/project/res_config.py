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

from osv import fields, osv
import pooler
from tools.translate import _

class project_configuration(osv.osv_memory):
    _inherit = 'project.config.settings'

    _columns = {
        'module_project_mrp': fields.boolean('Allow to create tasks directly from a sale order',
                           help ="""
                           Automatically creates project tasks from procurement lines.
                           It installs the project_mrp module.
                           """),
        'module_pad': fields.boolean("Write project specification on collaborative note pad",
                          help="""Lets the company customize which Pad installation should be used to link to new pads
                            (by default, http://ietherpad.com/).
                          It installs the pad module."""),
        'module_project_timesheet': fields.boolean("Invoice working time on task",
                        help="""This allows you to transfer the entries under tasks defined for Project Management to
                        the timesheet line entries for particular date and particular user  with the effect of creating, editing and deleting either ways.
                        It installs the project_timesheet module."""),
        'module_project_scrum': fields.boolean("Allow to manage your project on agile methodology",
                        help="""This allows to implement all concepts defined by the scrum project management methodology for IT companies.
                                * Project with sprints, product owner, scrum master
                                * Sprints with reviews, daily meetings, feedbacks
                                * Product backlog
                                * Sprint backlog.
                            It installs the project_scrum module."""),
        'module_project_planning' : fields.boolean("Manage planning",
                        help="""This module helps you to manage your plannings.
                            each department manager can know if someone in his team has still unallocated time for a given planning (taking in consideration the validated leaves) or if he still needs to encode tasks.
                        It Installs project_planning  module."""),
        'module_project_long_term': fields.boolean("Manage Long term planning",
                        help="""Long Term Project management module that tracks planning, scheduling, resources allocation.
                        It installs the project_long_term module."""),
        'module_project_issue_sheet': fields.boolean("Track and invoice working time",
                        help="""Allows to the timesheet support for the Issues/Bugs Management in Project.
                        It installs the project_issue_sheet module."""),
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

project_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: