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

from osv import fields, osv

class project_installer(osv.osv_memory):
    _inherit = 'base.setup.installer'

    _columns = {
        # Project Management
        'project_long_term': fields.boolean(
        'Long Term Planning',
            help="Enables long-term projects tracking, including "
                 "multiple-phase projects and resource allocation handling."),
        'hr_timesheet_sheet': fields.boolean('Timesheets',
            help="Tracks and helps employees encode and validate timesheets "
                 "and attendances."),
        'project_timesheet': fields.boolean('Bill Time on Tasks',
            help="Helps generate invoices based on time spent on tasks, if activated on the project."),
        'account_budget': fields.boolean('Budgets',
            help="Helps accountants manage analytic and crossover budgets."),
        'project_issue': fields.boolean('Issues Tracker',
            help="Automatically synchronizes project tasks and crm cases."),
        # Methodologies
        'project_scrum': fields.boolean('Methodology: SCRUM',
            help="Implements and tracks the concepts and task types defined "
                 "in the SCRUM methodology."),
        'project_gtd': fields.boolean('Methodology: Getting Things Done',
            help="GTD is a methodology to efficiently organise yourself and your tasks. This module fully integrates GTD principle with OpenERP's project management."),
        'project_todo': fields.boolean('Project TODO', help=" add a project todo list in your Opportunities form."),
    }
project_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
