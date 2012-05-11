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

class project_configuration(osv.osv_memory):
    _name = 'project.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_project_mrp': fields.boolean('Create Tasks from a Sale Order',
            help ="""This feature automatically creates project tasks from service products in sale orders.
                More precisely, tasks are created for procurement lines with product of type 'Service',
                procurement method 'Make to Order', and supply method 'Produce'.
                This installs the module project_mrp."""),
        'module_pad': fields.boolean("Use Collaborative Note Pads for Tasks",
            help="""Lets the company customize which Pad installation should be used to link to new pads
                (by default, http://ietherpad.com/).
                This installs the module pad."""),
        'module_project_timesheet': fields.boolean("Timesheets and Invoices",
            help="""This allows you to transfer the entries under tasks defined for Project Management to
                the timesheet line entries for particular date and user, with the effect of creating,
                editing and deleting either ways.
                This installs the module project_timesheet."""),
        'module_project_long_term': fields.boolean("Manage Gantt and Resource Planning",
            help="""A long term project management module that tracks planning, scheduling, and resource allocation.
                This installs the module project_long_term."""),
        'module_project_issue': fields.boolean("Issues and Bug Tracking",
            help="""Provides management of issues/bugs in projects.
                This installs the module project_issue."""),
        'module_project_issue_sheet': fields.boolean("Track and Invoice Issues Working Time",
            help="""Provides timesheet support for the issues/bugs management in project.
                This installs the module project_issue_sheet."""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
