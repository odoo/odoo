# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
{
    "name" : "Scrum, Agile Development Method",
    "version": "1.0",
    "author" : "Tiny",
    "depends" : ["project", "process"],
    "category" : "Enterprise Specific Modules/Information Technology",
    "init_xml" : [],
    "description": """
    This modules implements all concepts defined by the scrum project
    management methodology for IT companies:
    * Project with sprints, product owner, scrum master
    * Sprints with reviews, daily meetings, feedbacks
    * Product backlog
    * Sprint backlog

    It adds some concepts to the project management module:
    * Mid-term, long-term roadmaps
    * Customers/functionnal requests, vs technical ones

    It also create a new reporting:
    * Burndown chart

    The scrum projects and tasks inherits from the real projects and
    tasks, so you can continue working on normal tasks that will also
    include tasks from scrum projects.

    More information on the methodology:
    * http://controlchaos.com
    """,
    "demo_xml" : ["scrum_demo.xml"],
    "update_xml": [
        "security/ir.model.access.csv",
        "scrum_view.xml",
        "scrum_report.xml",
        "scrum_wizard.xml",
        "process/scrum_process.xml",
    ],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

