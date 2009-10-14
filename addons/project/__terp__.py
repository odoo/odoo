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


{
    "name" : "Project Management",
    "version": "1.1",
    "author" : "Tiny",
    "website" : "http://www.openerp.com",
    "category" : "Generic Modules/Projects & Services",
    "depends" : ["product", "account", "hr", "process"],
    "description": """Project management module that track multi-level projects, tasks,
works done on tasks, eso. It is able to render planning, order tasks, eso.
    """,
    "init_xml" : [],
    "demo_xml" : ["project_demo.xml"],
    "update_xml": [
        "security/project_security.xml",
        "security/ir.model.access.csv",
        "project_data.xml", 
        "project_wizard.xml", 
        "project_view.xml", 
        "project_report.xml", 
        "process/task_process.xml"
    ],
    'demo_xml': ['project_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0075116868317',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
