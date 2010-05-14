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
    _name = 'project.installer'
    _inherit = 'res.config.installer'

    _columns = {
        # Project Management
        'project_long_term':fields.boolean('Long Term Planning',
            help="Enables long-term projects tracking, including "
                 "multiple-phase projects and resource allocation handling."),
        'project_wiki':fields.boolean('Specifications in a Wiki',
            help=""),
        'hr_timesheet_sheet':fields.boolean('Timesheets',
            help="Tracks and helps employees encode and validate timesheets "
                 "and attendance."),
        'hr_timesheet_invoice':fields.boolean('Invoice Based on Hours',
            help="Helps generate invoice based on based on human resources "
                 "costs and general expenses."),
        'account_budget':fields.boolean('Budgets',
            help="Helps accountants manage analytic and crossover budgets."),
        'project_messages':fields.boolean('Project Messages',
            help="Lets employees send messages to other members of the "
                 "projects they're working on."),
        'project_crm':fields.boolean('Issues Tracker',
            help="Automatically synchronizes project tasks and crm cases."),
        # Methodologies
        'scrum':fields.boolean('SCRUM',
            help="Implements and tracks the concepts and task types defined "
                 "in the SCRUM methodology."),
        'project_gtd':fields.boolean('Getting Things Done',
            help="Embeds the Getting Things Done concepts into OpenERP's "
                 "project management."),
        }
    _defaults={
             'project_crm': True,
               }
project_installer()
