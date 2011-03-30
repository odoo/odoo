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


{
    'name': 'Scrum, Agile Development Method',
    'version': '1.0',
    'category': 'Project Management',
    'description': """
This module implements all concepts defined by the scrum project management methodology for IT companies.
=========================================================================================================

    * Project with sprints, product owner, scrum master
    * Sprints with reviews, daily meetings, feedbacks
    * Product backlog
    * Sprint backlog

It adds some concepts to the project management module:
    * Mid-term, long-term road-map
    * Customers/functional requests VS technical ones

It also creates a new reporting:
    * Burn-down chart

The scrum projects and tasks inherit from the real projects and
tasks, so you can continue working on normal tasks that will also
include tasks from scrum projects.

More information on the methodology:
    * http://controlchaos.com
    """,
    'author': 'OpenERP SA',
    'images': ['images/product_backlogs.jpeg', 'images/project_sprints.jpeg', 'images/scrum_dashboard.jpeg', 'images/scrum_meetings.jpeg'],
    'depends': ['project', 'process', 'email'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'project_scrum_report.xml',
        'wizard/project_scrum_backlog_create_task_view.xml',
        'wizard/project_scrum_backlog_merger_view.xml',
        'wizard/project_scrum_postpone_view.xml',
#        "wizard/project_scrum_email_view.xml",
        'project_scrum_view.xml',
        'wizard/project_scrum_backlog_sprint_view.xml',
        'process/project_scrum_process.xml',
        "board_project_scrum_view.xml",
    ],
    'demo_xml': ['project_scrum_demo.xml'],
    'test': ['test/project_scrum_report.yml'],
    'installable': True,
    'active': False,
    'certificate' : '00736750152003010781',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
